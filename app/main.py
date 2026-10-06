from .lib.exceptions import InvalidDataException, InvalidFunctionException, InvalidParamsException
from .lib.params import Params
from .lib.response import Response
from .routes.routes import route
from .utils.pagination import PaginatedResult
import traceback

CLIENT_FACING_EXCEPTIONS = (InvalidDataException, InvalidFunctionException, InvalidParamsException)
UNIQUE_VIOLATION_PGCODE = "23505"


def _error_message(ex: Exception) -> str:
    if isinstance(ex, CLIENT_FACING_EXCEPTIONS):
        return f"GeneralException: {type(ex).__name__}-{str(ex)}"
    inner = ex.args[0] if ex.args else None
    if getattr(inner, "pgcode", None) == UNIQUE_VIOLATION_PGCODE:
        return "GeneralException: DuplicateError-a record with these values already exists"
    return "GeneralException: InternalError-something went wrong, please try again"


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
        return Response.generate(
            message=_error_message(ex)
        )
