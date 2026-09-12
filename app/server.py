"""FastAPI adapter for local/Docker deployment.

Wraps the same framework-agnostic ``app.main.main`` entrypoint used by the
AWS Lambda handler (``app.response_handler.lambda_handler``), so request
handling logic never forks between the two deployment targets. A request is
translated into the API-Gateway-shaped ``event`` dict that ``Params.from_event``
already knows how to parse, so both deployments share identical param/auth
parsing.

Auth note: in real deployments the ``sub`` claim is populated by an API
Gateway Cognito authorizer. There is no authorizer here, so the caller must
supply the user id directly via the ``X-User-Id`` header.
"""

from .lib.params import Params
from .lib.exceptions import InvalidParamsException
from .main import main
from .routes.routes import extract_path_params

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

app = FastAPI(title="dompet")

_CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "OPTIONS, GET, POST, PUT, DELETE",
    "Access-Control-Allow-Headers": "Content-Type, Authorization, X-User-Id",
}


@app.exception_handler(InvalidParamsException)
async def invalid_params_handler(request: Request, exc: InvalidParamsException) -> JSONResponse:
    # Params.from_event runs before main()'s own try/except, so a missing/bad
    # user id (no X-User-Id header, since there's no Cognito authorizer here)
    # would otherwise surface as an unhandled 500.
    return JSONResponse(
        status_code=401,
        content={"success": False, "data": None, "metadata": {}, "message": exc.message},
        headers=_CORS_HEADERS,
    )


async def _build_event(request: Request) -> dict:
    body_bytes = await request.body()
    body = body_bytes.decode("utf-8") if body_bytes else None
    user_id = request.headers.get("x-user-id")

    # Unlike API Gateway (which parses path params itself from its own
    # resource-path config before Lambda ever sees the event), there's no
    # such source here, so path params are pulled from the same route
    # patterns app.routes.routes uses to dispatch.
    path_params = extract_path_params(request.url.path, request.method)

    return {
        "httpMethod": request.method,
        "path": request.url.path,
        "headers": dict(request.headers),
        "body": body,
        "queryStringParameters": dict(request.query_params) or None,
        "pathParameters": path_params,
        "requestContext": {
            "authorizer": {
                "claims": {"sub": user_id},
            },
        },
    }


@app.api_route(
    "/{full_path:path}",
    methods=["GET", "POST", "PUT", "DELETE"],
)
async def dispatch(full_path: str, request: Request) -> Response:
    event = await _build_event(request)
    params = Params.from_event(event)
    response = main(params)
    # model_dump_json (not model_dump) so UUID/Decimal/datetime fields inside
    # `data` (typed Any/List[Any], so pydantic can't infer them structurally)
    # serialize the same way AWSLambdaResponse.generate already does for Lambda.
    return Response(
        content=response.model_dump_json(exclude_none=True),
        media_type="application/json",
        headers=_CORS_HEADERS,
    )
