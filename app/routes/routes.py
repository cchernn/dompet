from ..lib.params import Params
from ..lib.response import Response
from ..lib.exceptions import InvalidFunctionException
from ..handlers import transaction
from ..handlers import group
from ..handlers import attachment
from ..handlers import location

import re
from typing import Callable

routes = {
    (re.compile(r"^/transactions$"), "GET", transaction.list),
    (re.compile(r"^/transactions$"), "POST", transaction.add),
    (re.compile(r"^/transactions/\d+$"), "GET", transaction.get),
    (re.compile(r"^/transactions/\d+$"), "PUT", transaction.edit),
    (re.compile(r"^/transactions/\d+$"), "DELETE", transaction.delete),
    (re.compile(r"^/groups$"), "GET", group.list),
    (re.compile(r"^/groups$"), "POST", group.add),
    (re.compile(r"^/groups/\d+$"), "GET", group.get),
    (re.compile(r"^/groups/\d+$"), "PUT", group.edit),
    (re.compile(r"^/groups/\d+$"), "DELETE", group.delete),
    (re.compile(r"^/attachments$"), "GET", attachment.list),
    # (re.compile(r"^/attachments$"), "POST", attachment.create),
    # (re.compile(r"^/attachments/\d+$"), "GET", attachment.get),
    # (re.compile(r"^/attachments/\d+$"), "PUT", attachment.edit),
    # (re.compile(r"^/attachments/\d+$"), "DELETE", attachment.delete),
    (re.compile(r"^/locations$"), "GET", location.list),
    (re.compile(r"^/locations$"), "POST", location.add),
    (re.compile(r"^/locations/\d+$"), "GET", location.get),
    (re.compile(r"^/locations/\d+$"), "PUT", location.edit),
    (re.compile(r"^/locations/\d+$"), "DELETE", location.delete),
}

def match_route(path: str, method: str):
    for pattern, http_method, func in routes:
        if http_method == method and pattern.match(path):
            return func
    return None

def route(params: Params) -> Callable[[Params], Response]:
    func = match_route(params.path, params.http_method)
    if not func:
        raise InvalidFunctionException(f"Function for path is not found: {params.path}")
    return func