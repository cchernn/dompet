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

    (re.compile(r"^/locations$"), "GET", location.list),
    (re.compile(r"^/locations$"), "POST", location.add),
    (re.compile(rf"^/locations/{_uuid('location_id')}$"), "GET", location.get),

    (re.compile(rf"^/accounts/{_uuid('account_id')}/locations$"), "GET", account_location.list),
    (re.compile(rf"^/accounts/{_uuid('account_id')}/locations$"), "POST", account_location.add),
    (re.compile(rf"^/accounts/{_uuid('account_id')}/locations/{_uuid('location_id')}$"), "DELETE", account_location.delete),

    (re.compile(r"^/tags$"), "GET", tag.list),
    (re.compile(r"^/tags$"), "POST", tag.add),

    (re.compile(rf"^/transactions/{_uuid('transaction_id')}/tags$"), "GET", transaction_tag.list),
    (re.compile(rf"^/transactions/{_uuid('transaction_id')}/tags$"), "POST", transaction_tag.add),
    (re.compile(rf"^/transactions/{_uuid('transaction_id')}/tags/{_uuid('tag_id')}$"), "DELETE", transaction_tag.delete),
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
