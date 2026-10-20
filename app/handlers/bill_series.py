from ..lib.params import Params
from ..models.bill_series import BillSeries
from ..db import bill_series as bill_series_db
from ..utils.pagination import PaginatedResult, parse_pagination


def _include_inactive(params: Params) -> bool:
    if not params.queryParams:
        return False
    return str(params.queryParams.get("include_inactive", "")).lower() == "true"


def list(params: Params) -> PaginatedResult:
    page, page_size = parse_pagination(params)
    rows, metadata = bill_series_db.list_series(params.user, page, page_size, include_inactive=_include_inactive(params))
    return PaginatedResult([BillSeries(**row) for row in rows], metadata)


def get(params: Params) -> BillSeries:
    series_id = params.pathParams.get("series_id")
    row = bill_series_db.get_series(params.user, series_id)
    return BillSeries(**row)


def add(params: Params) -> BillSeries:
    body = params.body or {}
    row = bill_series_db.create_series(params.user, body)
    return BillSeries(**row)


def edit(params: Params) -> BillSeries:
    series_id = params.pathParams.get("series_id")
    body = params.body or {}
    row = bill_series_db.update_series(params.user, series_id, body)
    return BillSeries(**row)


def delete(params: Params) -> BillSeries:
    series_id = params.pathParams.get("series_id")
    row = bill_series_db.deactivate_series(params.user, series_id)
    return BillSeries(**row)
