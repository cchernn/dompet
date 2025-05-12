from .lib.params import Params
from .lib.response import AWSLambdaResponse
from .main import main

from typing import Any

def lambda_handler(event: dict, context: Any) -> AWSLambdaResponse:
    params = Params.from_event(event)
    response = main(params)
    return AWSLambdaResponse.generate(
        params=params,
        response=response,
    ).model_dump_json()