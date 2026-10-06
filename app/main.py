from .lib.exceptions import (
    InvalidDataException,
    InvalidFunctionException,
    InvalidParamsException,
    NotFoundException,
)
from .lib.params import Params
from .lib.response import Response
from .routes.routes import route
from .utils.pagination import PaginatedResult
import traceback

UNIQUE_VIOLATION_PGCODE = "23505"


def _error_response(ex: Exception) -> tuple[int, str]:
    if isinstance(ex, NotFoundException):
        return 404, f"GeneralException: {type(ex).__name__}-{str(ex)}"
    if isinstance(ex, InvalidFunctionException):
        return 404, f"GeneralException: {type(ex).__name__}-{str(ex)}"
    if isinstance(ex, (InvalidDataException, InvalidParamsException)):
        return 400, f"GeneralException: {type(ex).__name__}-{str(ex)}"
    inner = ex.args[0] if ex.args else None
    if getattr(inner, "pgcode", None) == UNIQUE_VIOLATION_PGCODE:
        return 409, "GeneralException: DuplicateError-a record with these values already exists"
    return 500, "GeneralException: InternalError-something went wrong, please try again"


def main(params: Params) -> Response:
    try:
        func = route(params)
        result = func(params)
        if isinstance(result, PaginatedResult):
            return Response.generate(
                data=result.items,
                metadata=result.metadata,
            )
        return Response.generate(
            data=result,
        )
    except Exception as ex:
        traceback.print_exc()
        status_code, message = _error_response(ex)
        return Response.generate(message=message, status_code=status_code)
