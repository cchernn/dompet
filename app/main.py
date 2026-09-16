from .lib.params import Params
from .lib.response import Response
from .routes.routes import route
from .utils.pagination import PaginatedResult
import traceback

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
        message = f"GeneralException: {type(ex).__name__}-{str(ex)}"
        print(message)
        return Response.generate(
            message=message
        )