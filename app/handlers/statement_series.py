from ..lib.params import Params
from ..models.statement_series import StatementSeries
from ..db import statement_series as statement_series_db
from ..utils.pagination import PaginatedResult, parse_pagination


def _include_inactive(params: Params) -> bool:
    if not params.queryParams:
        return False
    return str(params.queryParams.get("include_inactive", "")).lower() == "true"


def list(params: Params) -> PaginatedResult:
    page, page_size = parse_pagination(params)
    rows, metadata = statement_series_db.list_series(params.user, page, page_size, include_inactive=_include_inactive(params))
    return PaginatedResult([StatementSeries(**row) for row in rows], metadata)


def get(params: Params) -> StatementSeries:
    series_id = params.pathParams.get("series_id")
    row = statement_series_db.get_series(params.user, series_id)
    return StatementSeries(**row)


def add(params: Params) -> StatementSeries:
    body = params.body or {}
    row = statement_series_db.create_series(params.user, body)
    return StatementSeries(**row)


def edit(params: Params) -> StatementSeries:
    series_id = params.pathParams.get("series_id")
    body = params.body or {}
    row = statement_series_db.update_series(params.user, series_id, body)
    return StatementSeries(**row)


def delete(params: Params) -> StatementSeries:
    series_id = params.pathParams.get("series_id")
    row = statement_series_db.deactivate_series(params.user, series_id)
    return StatementSeries(**row)
