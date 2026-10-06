from .lib.exceptions import InvalidParamsException
from .lib.params import Params
from .lib.response import Response, AWSLambdaResponse
from .main import error_response, main
from .utils.env import load_local_env

from typing import Any

def lambda_handler(event: dict, context: Any) -> AWSLambdaResponse:
    try:
        params = Params.from_event(event)
    except InvalidParamsException as ex:
        status_code, message = error_response(ex)
        return AWSLambdaResponse.generate(
            params=None,
            response=Response.generate(message=message, status_code=status_code),
        ).model_dump()
    response = main(params)
    return AWSLambdaResponse.generate(
        params=params,
        response=response,
    ).model_dump()

def local_handler(event: dict) -> Response:
    load_local_env()
    params = Params.from_local(event)
    return main(params)
