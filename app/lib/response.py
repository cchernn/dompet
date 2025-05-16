from ..lib.params import Params

import json
from pydantic import BaseModel, Field
from typing import Optional, Literal, Union, Any, List

class Response(BaseModel):
    success: bool = Field(
        False,
        title="API Response Title",
        description="Status of the API Response. Default: False"
    )
    data: Optional[Union[Any, List[Any]]] = Field(
        None,
        title="API Response Data",
        description="Data returned by the API call"
    )
    metadata: Optional[dict] = Field(
        {},
        title="API Response Metadata",
        description="Metadata for the response"
    )
    message: Optional[str] = Field(
        None,
        title="API Response Message",
        description="Error message for the response",
    )

    @classmethod
    def generate(cls, data: Optional[Union[list, dict]] = None, message: Optional[str] = None) -> "Response":
        success = False if message else True
        return cls(
            success=success,
            data=data,
            message=message,
        )

class AWSLambdaResponse(BaseModel):
    statusCode: Literal[
        200,
        201,
        400,
        401,
        403,
        404,
        500,
    ] = Field(
        500,
        title="API Response Code",
        description="API Response Code. Default: 500"
    )
    headers: dict = Field(
        ...,
        title="API Response headers",
        description="Headers for the API Response"
    )
    body: Optional[dict] = Field(
        None,
        title="API Response Body",
        description="Body object for the API Response"
    )

    @classmethod
    def generate(cls, params: Params, response: Response) -> "AWSLambdaResponse":
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "OPTIONS, GET, POST, PUT, DELETE",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        }
        status_code = 200 # WIP: insert status_code logic here
        body = response.model_dump(exclude_none=True)

        return cls(
            statusCode=status_code,
            headers=headers,
            body=body,
        )