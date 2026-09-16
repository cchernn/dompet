from ..lib.params import Params
from ..lib.response import Response
from ..lib.exceptions import InvalidFunctionException
from ..handlers import transaction
from ..handlers import account
from ..handlers import category
from ..handlers import location
from ..handlers import account_location
from ..handlers import tag
from ..handlers import transaction_tag
from ..handlers import attachment
from ..handlers import transaction_attachment
from ..handlers import budget
from ..handlers import budget_member
from ..handlers import transaction_budget

import re
from typing import Callable, Optional

UUID_RE = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"


def _uuid(name: str) -> str:
    """A UUID segment captured as a named group, so callers that don't have
    their own path-param source (e.g. the local FastAPI adapter, unlike API
    Gateway) can extract path params straight from the route pattern."""
    return rf"(?P<{name}>{UUID_RE})"


routes = {
    (re.compile(r"^/transactions$"), "GET", transaction.list),
    (re.compile(r"^/transactions$"), "POST", transaction.add),
    (re.compile(rf"^/transactions/{_uuid('transaction_id')}$"), "GET", transaction.get),
    (re.compile(rf"^/transactions/{_uuid('transaction_id')}$"), "PUT", transaction.edit),
    (re.compile(rf"^/transactions/{_uuid('transaction_id')}/deactivate$"), "POST", transaction.deactivate),
    (re.compile(rf"^/transactions/{_uuid('transaction_id')}/reactivate$"), "POST", transaction.reactivate),
    (re.compile(rf"^/transactions/{_uuid('transaction_id')}/rollback$"), "POST", transaction.rollback),

    (re.compile(r"^/accounts$"), "GET", account.list),
    (re.compile(r"^/accounts$"), "POST", account.add),
    (re.compile(rf"^/accounts/{_uuid('account_id')}$"), "GET", account.get),
    (re.compile(rf"^/accounts/{_uuid('account_id')}$"), "PUT", account.edit),
    (re.compile(rf"^/accounts/{_uuid('account_id')}/deactivate$"), "POST", account.deactivate),
    (re.compile(rf"^/accounts/{_uuid('account_id')}/reactivate$"), "POST", account.reactivate),

    (re.compile(r"^/categories$"), "GET", category.list),
    (re.compile(r"^/categories$"), "POST", category.add),
    (re.compile(rf"^/categories/{_uuid('category_id')}$"), "PUT", category.edit),
    (re.compile(rf"^/categories/{_uuid('category_id')}$"), "DELETE", category.delete),

    (re.compile(r"^/locations$"), "GET", location.list),
    (re.compile(r"^/locations$"), "POST", location.add),
    (re.compile(rf"^/locations/{_uuid('location_id')}$"), "GET", location.get),
    (re.compile(rf"^/locations/{_uuid('location_id')}$"), "PUT", location.edit),
    (re.compile(rf"^/locations/{_uuid('location_id')}$"), "DELETE", location.delete),

    (re.compile(rf"^/accounts/{_uuid('account_id')}/locations$"), "GET", account_location.list),
    (re.compile(rf"^/accounts/{_uuid('account_id')}/locations$"), "POST", account_location.add),
    (re.compile(rf"^/accounts/{_uuid('account_id')}/locations/{_uuid('location_id')}$"), "DELETE", account_location.delete),

    (re.compile(r"^/tags$"), "GET", tag.list),
    (re.compile(r"^/tags$"), "POST", tag.add),
    (re.compile(rf"^/tags/{_uuid('tag_id')}$"), "PUT", tag.edit),
    (re.compile(rf"^/tags/{_uuid('tag_id')}$"), "DELETE", tag.delete),

    (re.compile(rf"^/transactions/{_uuid('transaction_id')}/tags$"), "GET", transaction_tag.list),
    (re.compile(rf"^/transactions/{_uuid('transaction_id')}/tags$"), "POST", transaction_tag.add),
    (re.compile(rf"^/transactions/{_uuid('transaction_id')}/tags/{_uuid('tag_id')}$"), "DELETE", transaction_tag.delete),

    (re.compile(r"^/attachments$"), "GET", attachment.list),
    (re.compile(r"^/attachments$"), "POST", attachment.add),
    (re.compile(rf"^/attachments/{_uuid('attachment_id')}$"), "GET", attachment.get),
    (re.compile(rf"^/attachments/{_uuid('attachment_id')}$"), "PUT", attachment.edit),
    (re.compile(rf"^/attachments/{_uuid('attachment_id')}$"), "DELETE", attachment.delete),

    (re.compile(rf"^/transactions/{_uuid('transaction_id')}/attachments$"), "GET", transaction_attachment.list),
    (re.compile(rf"^/transactions/{_uuid('transaction_id')}/attachments$"), "POST", transaction_attachment.add),
    (re.compile(rf"^/transactions/{_uuid('transaction_id')}/attachments/{_uuid('attachment_id')}$"), "DELETE", transaction_attachment.delete),

    (re.compile(r"^/budgets$"), "GET", budget.list),
    (re.compile(r"^/budgets$"), "POST", budget.add),
    (re.compile(rf"^/budgets/{_uuid('budget_id')}$"), "GET", budget.get),
    (re.compile(rf"^/budgets/{_uuid('budget_id')}$"), "PUT", budget.edit),
    (re.compile(rf"^/budgets/{_uuid('budget_id')}$"), "DELETE", budget.delete),

    (re.compile(rf"^/budgets/{_uuid('budget_id')}/transactions$"), "GET", budget.list_transactions),

    (re.compile(rf"^/budgets/{_uuid('budget_id')}/members$"), "GET", budget_member.list),
    (re.compile(rf"^/budgets/{_uuid('budget_id')}/members$"), "POST", budget_member.add),
    (re.compile(rf"^/budgets/{_uuid('budget_id')}/members/{_uuid('member_user_id')}$"), "DELETE", budget_member.delete),

    (re.compile(rf"^/transactions/{_uuid('transaction_id')}/budgets$"), "GET", transaction_budget.list),
    (re.compile(rf"^/transactions/{_uuid('transaction_id')}/budgets$"), "POST", transaction_budget.add),
    (re.compile(rf"^/transactions/{_uuid('transaction_id')}/budgets/{_uuid('budget_id')}$"), "DELETE", transaction_budget.delete),
}

def match_route(path: str, method: str):
    for pattern, http_method, func in routes:
        if http_method == method and pattern.match(path):
            return func
    return None


def extract_path_params(path: str, method: str) -> Optional[dict]:
    """Named UUID groups captured from the matching route pattern, for
    callers with no path-param source of their own (API Gateway parses these
    for Lambda; the local FastAPI adapter has to do it itself)."""
    for pattern, http_method, _func in routes:
        if http_method == method:
            match = pattern.match(path)
            if match:
                return match.groupdict() or None
    return None

def route(params: Params) -> Callable[[Params], Response]:
    func = match_route(params.path, params.http_method)
    if not func:
        raise InvalidFunctionException(f"Function for path is not found: {params.path}")
    return func
