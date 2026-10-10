import re
from datetime import datetime, timezone

from ..lib.params import Params
from ..lib.exceptions import InvalidDataException
from ..models.assistant import AssistantReply
from ..utils import bedrock
from . import transaction_insights
from . import budget_insights

MAX_TOOL_ROUNDS = 3

FALLBACK_REPLY = (
    "I wasn't able to fully resolve that question. Try rephrasing it or "
    "narrowing the date range."
)

_FILTER_PROPERTIES = {
    "from": {"type": "string", "description": "Start date, inclusive, YYYY-MM-DD"},
    "to": {"type": "string", "description": "End date, inclusive, YYYY-MM-DD"},
    "category": {"type": "string", "description": "Exact category name"},
    "type": {"type": "string", "enum": ["income", "expenditure", "transfer"]},
    "source": {"type": "string", "description": "Exact source account name"},
    "destination": {"type": "string", "description": "Exact destination account name"},
    "tags": {"type": "string", "description": "Exact tag name"},
    "budgets": {"type": "string", "description": "Exact budget name"},
}

_BUCKET_PROPERTY = {
    "bucket": {
        "type": "string",
        "enum": ["day", "week", "month"],
        "description": "Bucket size for the time series. Default day.",
    }
}

_BUDGET_FILTER_PROPERTIES = {
    "q": {"type": "string", "description": "Budget name substring, case-insensitive"},
    "from": {"type": "string", "description": "Start date, inclusive, YYYY-MM-DD"},
    "to": {"type": "string", "description": "End date, inclusive, YYYY-MM-DD"},
}

TOOLS = [
    {
        "toolSpec": {
            "name": "get_transaction_summary",
            "description": (
                "Aggregate income/expense totals for the user's transactions, with "
                "breakdowns by category, source account, and budget. Use for questions "
                "about totals or spending by category/account/budget over a period."
            ),
            "inputSchema": {"json": {"type": "object", "properties": _FILTER_PROPERTIES}},
        }
    },
    {
        "toolSpec": {
            "name": "get_transaction_trend",
            "description": (
                "Bucketed income/expense/net time series for the user's transactions. "
                "Use for questions about trends over time."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {**_BUCKET_PROPERTY, **_FILTER_PROPERTIES},
                }
            },
        }
    },
    {
        "toolSpec": {
            "name": "get_budget_summary",
            "description": (
                "Aggregate totals (budget count, total income/expense, net) and a "
                "breakdown by budget. Use for questions about budgets overall or a "
                "specific named budget."
            ),
            "inputSchema": {"json": {"type": "object", "properties": _BUDGET_FILTER_PROPERTIES}},
        }
    },
    {
        "toolSpec": {
            "name": "get_budget_trend",
            "description": (
                "Bucketed income/expense/net time series across budgets matching a "
                "filter. Use for budget trend-over-time questions."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {**_BUCKET_PROPERTY, **_BUDGET_FILTER_PROPERTIES},
                }
            },
        }
    },
]

_TOOL_DISPATCH = {
    "get_transaction_summary": transaction_insights.summary,
    "get_transaction_trend": transaction_insights.trend,
    "get_budget_summary": budget_insights.summary,
    "get_budget_trend": budget_insights.trend,
}


def _system_prompt() -> list:
    today = datetime.now(timezone.utc).date().isoformat()
    text = (
        f"You are a financial assistant for the Dompet app. Today's date is {today} "
        "(UTC). Answer the user's question about their own transactions and budgets "
        "using only the provided tools -- never invent numbers. Amounts are each "
        "account's native currency; there is no currency conversion between accounts. "
        "Only pass from/to to a tool if the user's question actually mentions a time "
        "period (e.g. \"last month\", \"this week\", a specific range) -- resolve that "
        "into explicit dates. If no time period is mentioned, call the tool with no "
        "date filter at all so it covers all time; never default to a recent window on "
        "your own. If a category, account, or budget name in the question is ambiguous, "
        "ask a clarifying question instead of guessing. Respond with only your final "
        "answer in plain prose -- never include your reasoning, planning, or any "
        "<thinking> block in the reply."
    )
    return [{"text": text}]


_THINKING_BLOCK_RE = re.compile(r"<thinking>.*?</thinking>", re.IGNORECASE | re.DOTALL)


def _strip_thinking(text: str) -> str:
    """Nova Micro sometimes puts its reasoning directly in the text block
    instead of a separate one -- the system prompt asks it not to, but that
    alone isn't reliable enough to guarantee it never leaks through."""
    return _THINKING_BLOCK_RE.sub("", text).strip()


def _run_tool(params: Params, name: str, tool_input: dict) -> dict:
    handler = _TOOL_DISPATCH.get(name)
    if handler is None:
        raise InvalidDataException(ValueError(f"unknown tool: {name}"))
    tool_params = Params(user=params.user, queryParams=tool_input or {})
    result = handler(tool_params)
    return result.model_dump(mode="json")


def query(params: Params) -> AssistantReply:
    body = params.body or {}
    message = (body.get("message") or "").strip()
    if not message:
        raise InvalidDataException(ValueError("message is required"))

    messages = [{"role": "user", "content": [{"text": message}]}]

    for round_number in range(1, MAX_TOOL_ROUNDS + 1):
        response = bedrock.converse(messages=messages, system=_system_prompt(), tools=TOOLS)
        output_message = response["output"]["message"]
        messages.append(output_message)
        stop_reason = response.get("stopReason")

        tool_uses = [block["toolUse"] for block in output_message["content"] if "toolUse" in block]
        print(f"assistant.query round={round_number} stopReason={stop_reason} tools={[t['name'] for t in tool_uses]}")
        if not tool_uses:
            text = "".join(block.get("text", "") for block in output_message["content"])
            text = _strip_thinking(text)
            return AssistantReply(reply=text or FALLBACK_REPLY)

        result_blocks = []
        for tool_use in tool_uses:
            try:
                tool_result = _run_tool(params, tool_use["name"], tool_use.get("input") or {})
                result_blocks.append({
                    "toolResult": {
                        "toolUseId": tool_use["toolUseId"],
                        "content": [{"json": tool_result}],
                    }
                })
            except Exception as ex:
                print(f"assistant.query round={round_number} tool={tool_use['name']} error={type(ex).__name__}: {ex}")
                result_blocks.append({
                    "toolResult": {
                        "toolUseId": tool_use["toolUseId"],
                        "content": [{"text": str(ex)}],
                        "status": "error",
                    }
                })
        messages.append({"role": "user", "content": result_blocks})

    print(f"assistant.query hit MAX_TOOL_ROUNDS={MAX_TOOL_ROUNDS} without a final answer")
    return AssistantReply(reply=FALLBACK_REPLY)
