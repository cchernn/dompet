from ..lib.params import Params
from ..lib.response import Response
from ..lib.exceptions import InvalidFunctionException
from ..handlers import transaction
from ..handlers import group
from ..handlers import attachment
from ..handlers import location

from typing import Callable

routes = {
    (r"/transactions", "GET"): transaction.list,
    # (r"/transactions", "POST"): transaction.create,
    # (r"/transactions/\d+", "GET"): transaction.get,
    # (r"/transactions/\d+", "PUT"): transaction.edit,
    # (r"/transactions/\d+", "DELETE"): transaction.delete,
    (r"/groups", "GET"): group.list,
    # (r"/transactions/groups", "POST"): group.create,
    # (r"/transactions/groups/\d+", "GET"): group.get,
    # (r"/transactions/groups/\d+", "PUT"): group.edit,
    # (r"/transactions/groups/\d+", "DELETE"): group.delete,
    (r"/attachments", "GET"): attachment.list,
    # (r"/attachments", "POST"): attachment.create,
    # (r"/attachments/\d+", "GET"): attachment.get,
    # (r"/attachments/\d+", "PUT"): attachment.edit,
    # (r"/attachments/\d+", "DELETE"): attachment.delete,
    (r"/locations", "GET"): location.list,
    # (r"/locations", "POST"): location.create,
    # (r"/locations/\d+", "GET"): location.get,
    # (r"/locations/\d+", "PUT"): location.edit,
    # (r"/locations/\d+", "DELETE"): location.delete,   
}

def route(params: Params) -> Callable[[Params], Response]:
    func = routes.get((params.path, params.http_method))
    if not func:
        raise InvalidFunctionException(f"Function for path is not found: {params.path}")
    return func