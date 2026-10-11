import re
from datetime import datetime, timezone

from ..lib.params import Params
from ..lib.exceptions import InvalidDataException, InvalidParamsException
from ..models.assistant import AssistantReply
from ..utils import bedrock
from ..utils.pagination import PaginatedResult
from . import transaction_insights
from . import budget_insights
from . import transaction_search
from . import budget_search

MAX_TOOL_ROUNDS = 3
MAX_MESSAGE_LENGTH = 1000

# Search tools return individual rows, not aggregates -- each row carries
# several fields (name, amount, date, accounts, tags, budgets, ...), so an
# uncapped page would multiply token cost fast. The model never sees
# page/page_size as tool params; this is forced server-side regardless of
# what it asks for.
TOOL_SEARCH_PAGE_SIZE = 25

# Exceptions this app raises itself, with deliberately-written user-facing
# messages (bad bucket/filter values, missing fields) -- safe to hand back
# to the model as-is. Anything else (DB errors in particular, via
# DBOperationException) can carry raw SQL/schema text in str(ex).
_SAFE_TOOL_ERROR_TYPES = (InvalidDataException, InvalidParamsException)
_GENERIC_TOOL_ERROR = "This tool could not complete the request due to an internal error."

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
    {
        "toolSpec": {
            "name": "search_transactions",
            "description": (
                "List individual transactions matching filters, newest first, up to "
                f"{TOOL_SEARCH_PAGE_SIZE} results. Use for questions that need actual "
                "transaction line items rather than totals -- e.g. the biggest "
                "purchases, a list of transactions at a place, or transactions with "
                "a specific tag. For totals or breakdowns, use get_transaction_summary "
                "instead. category/source/destination/tags/budgets only match a name "
                "you already know exists exactly (e.g. one just seen in another tool's "
                "result) -- a non-matching value returns zero rows, not an error. For "
                "a word or phrase from the question itself with no confirmed exact "
                "match (e.g. a merchant or bill mentioned by name), use `q` instead, "
                "which matches as a substring of the transaction's own name, "
                "case-insensitively."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        **_FILTER_PROPERTIES,
                        "q": {
                            "type": "string",
                            "description": "Case-insensitive substring match on the transaction's own name",
                        },
                        "source_location": {"type": "string", "description": "Exact source location name"},
                        "destination_location": {"type": "string", "description": "Exact destination location name"},
                    },
                }
            },
        }
    },
    {
        "toolSpec": {
            "name": "search_budgets",
            "description": (
                "List budgets matching a name, up to "
                f"{TOOL_SEARCH_PAGE_SIZE} results, including each budget's owner, "
                "members, and when it was last updated. Use for questions about "
                "which budgets exist, who's in a budget, or when a budget was last "
                "updated. For totals or breakdowns, use get_budget_summary instead."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "q": {"type": "string", "description": "Budget name substring, case-insensitive"},
                    },
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
    "search_transactions": transaction_search.search,
    "search_budgets": budget_search.search,
}

_PAGINATED_TOOLS = frozenset({"search_transactions", "search_budgets"})


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
_UNCLOSED_THINKING_RE = re.compile(r"<thinking>.*", re.IGNORECASE | re.DOTALL)


def _strip_thinking(text: str) -> str:
    """Nova Micro sometimes puts its reasoning directly in the text block
    instead of a separate one -- the system prompt asks it not to, but that
    alone isn't reliable enough to guarantee it never leaks through. Also
    covers a response truncated mid-<thinking> block (no closing tag),
    where the well-formed-pair regex alone would miss it entirely."""
    text = _THINKING_BLOCK_RE.sub("", text)
    text = _UNCLOSED_THINKING_RE.sub("", text)
    return text.strip()


def _run_tool(params: Params, name: str, tool_input: dict) -> dict:
    handler = _TOOL_DISPATCH.get(name)
    if handler is None:
        raise InvalidDataException(ValueError(f"unknown tool: {name}"))
    query_params = dict(tool_input or {})
    if name in _PAGINATED_TOOLS:
        # Forced regardless of tool_input -- page/page_size aren't offered
        # to the model at all, so this only overrides a hallucinated value.
        query_params["page"] = 1
        query_params["page_size"] = TOOL_SEARCH_PAGE_SIZE
    tool_params = Params(user=params.user, queryParams=query_params)
    result = handler(tool_params)
    if isinstance(result, PaginatedResult):
        return {
            "items": [item.model_dump(mode="json") for item in result.items],
            "metadata": result.metadata,
        }
    return result.model_dump(mode="json")


def _sanitize_tool_error(ex: Exception) -> str:
    if isinstance(ex, _SAFE_TOOL_ERROR_TYPES):
        return str(ex)
    return _GENERIC_TOOL_ERROR


def _execute_tools(params: Params, tool_uses: list, round_number: int) -> list:
    result_blocks = []
    for tool_use in tool_uses:
        tool_use_id = tool_use.get("toolUseId", "unknown")
        tool_name = tool_use.get("name")
        try:
            if not tool_name:
                raise InvalidDataException(ValueError("malformed tool_use block from model: missing name"))
            tool_result = _run_tool(params, tool_name, tool_use.get("input") or {})
            result_blocks.append({
                "toolResult": {
                    "toolUseId": tool_use_id,
                    "content": [{"json": tool_result}],
                }
            })
        except Exception as ex:
            print(f"assistant.query round={round_number} tool={tool_name} error={type(ex).__name__}")
            result_blocks.append({
                "toolResult": {
                    "toolUseId": tool_use_id,
                    "content": [{"text": _sanitize_tool_error(ex)}],
                    "status": "error",
                }
            })
    return result_blocks


def _final_text(output_message: dict) -> str:
    text = "".join(block.get("text", "") for block in output_message["content"])
    return _strip_thinking(text)


def query(params: Params) -> AssistantReply:
    body = params.body or {}
    message = body.get("message")
    if not isinstance(message, str) or not message.strip():
        raise InvalidDataException(ValueError("message is required"))
    message = message.strip()
    if len(message) > MAX_MESSAGE_LENGTH:
        raise InvalidDataException(ValueError(f"message must be at most {MAX_MESSAGE_LENGTH} characters"))

    messages = [{"role": "user", "content": [{"text": message}]}]

    for round_number in range(1, MAX_TOOL_ROUNDS + 1):
        response = bedrock.converse(messages=messages, system=_system_prompt(), tools=TOOLS)
        output_message = response["output"]["message"]
        messages.append(output_message)
        stop_reason = response.get("stopReason")

        tool_uses = [block["toolUse"] for block in output_message["content"] if "toolUse" in block]
        print(f"assistant.query round={round_number} stopReason={stop_reason} tools={[t.get('name') for t in tool_uses]}")
        if not tool_uses:
            return AssistantReply(reply=_final_text(output_message) or FALLBACK_REPLY)

        result_blocks = _execute_tools(params, tool_uses, round_number)
        messages.append({"role": "user", "content": result_blocks})

    # MAX_TOOL_ROUNDS reached and the model still wanted another tool call on
    # the last round -- that round's tool results were already fetched and
    # appended above, so force one final answer-only call (no tools offered)
    # instead of discarding that work and returning the generic fallback.
    print(f"assistant.query hit MAX_TOOL_ROUNDS={MAX_TOOL_ROUNDS}, forcing a final answer-only call")
    response = bedrock.converse(messages=messages, system=_system_prompt())
    return AssistantReply(reply=_final_text(response["output"]["message"]) or FALLBACK_REPLY)
