from .exceptions import InvalidParamsException

import io
import cgi
import json
from pydantic import BaseModel, Field
from typing import Optional, Literal, Any
from uuid import UUID

class Params(BaseModel):
    user: UUID = Field(
        ...,
        title="Params User ID",
        description="User ID in UUID format",
    )
    http_method: Literal[
        "GET",
        "POST",
        "PUT",
        "DELETE"
    ] = Field(
        "GET",
        title="Params HTTP Method",
        description="HTTP Method of the API call. Default: GET",
    )
    path: str = Field(
        "",
        title="Params API Path",
        description="The API endpoint",
    )
    headers: Optional[dict[str, Any]] = Field(
        None,
        title="Params Headers",
        description="Headers of the API call",
    )
    body: Optional[dict[str, Any]] = Field(
        None,
        title="Params Body",
        description="The body object the API call",
    )
    queryParams: Optional[dict[str, Any]] = Field(
        None,
        title="Params Query Parameters",
        description="Query Paramenters of the API endpoint"
    )
    pathParams: Optional[dict[str, Any]] = Field(
        None,
        title="Params Path Parameters",
        description="Path Parameters of the API endpoint",
    )

    @classmethod
    def from_event(cls, event: dict) -> "Params":
        return cls(
            user = cls._parse_event_user_id(event),
            http_method = event.get("httpMethod"),
            path = event.get("path"),
            headers = cls._parse_event_headers(event),
            body = cls._parse_event_body(event),
            queryParams = event.get("queryStringParameters"),
            pathParams = event.get("pathParameters"),
        )
    
    @classmethod
    def from_local(cls, event: dict) -> "Params":
        return cls(
            user = event.get("user"),
            http_method = event.get("httpMethod"),
            path = event.get("path"),
            headers = event.get("headers"),
            body = event.get("body"),
            queryParams = event.get("queryParams"),
            pathParams = event.get("pathParams"),
        )
    
    @classmethod
    def _parse_event_user_id(cls, event: dict) -> UUID:
        try:
            user_id = (
                event.get("requestContext", {})
                .get("authorizer", {})
                .get("claims", {})
                .get("sub")
            )
            if not user_id:
                raise InvalidParamsException("Missing User ID from params")
            
            return UUID(user_id)
        except Exception as ex:
            raise InvalidParamsException(ex)
    
    @classmethod
    def _parse_event_headers(cls, event: dict) -> dict:
        headers = event.get("headers", {})
        return {k.lower(): v for k, v in headers.items()}
    
    @classmethod
    def _parse_event_body(cls, event: dict) -> dict:
        headers = cls._parse_event_headers(event)
        if event.get('body', None) not in [None, "None"]:
            content_type = headers.get("content-type")

            # form-data
            if "multipart/form-data" in content_type:
                fp = io.BytesIO(event.get("body").encode("utf-8"))
                pdict = cgi.parse_header(content_type)[1]
                if "boundary" in pdict:
                    pdict["boundary"] = pdict["boundary"].encode("utf-8")
                pdict["CONTENT-LENGTH"] = len(event.get("body"))
                body = cgi.parse_multipart(fp, pdict)
                for key, value in body.items():
                    if isinstance(value, list):
                        body[key] = value[0]
                return body
            
            # raw json
            elif "application/json" in content_type:
                return json.loads(event.get('body'))
            
            return event.get('body', None)
        return None
