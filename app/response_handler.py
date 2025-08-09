from .lib.params import Params
from .lib.response import Response, AWSLambdaResponse
from .main import main

from typing import Any

def lambda_handler(event: dict, context: Any) -> AWSLambdaResponse:
    params = Params.from_event(event)
    response = main(params)
    return AWSLambdaResponse.generate(
        params=params,
        response=response,
    ).model_dump()

def local_handler(event: dict) -> Response:
    params = Params.from_local(event)
    return main(params)
