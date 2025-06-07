from .lib.params import Params
from .lib.response import Response
from .routes.routes import route
import traceback

def main(params: Params) -> Response:
    try:
        func = route(params)
        data = func(params)
        return Response.generate(
            data=data,
        )
    except Exception as ex:
        traceback.print_exc()
        message = f"GeneralException: {type(ex).__name__}-{str(ex)}"
        print(message)
        return Response.generate(
            message=message
        )