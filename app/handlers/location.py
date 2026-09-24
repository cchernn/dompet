from ..lib.params import Params
from ..models.location import Location
from ..db import location as location_db
from ..utils.pagination import PaginatedResult, parse_pagination


def _include_inactive(params: Params) -> bool:
    if not params.queryParams:
        return False
    return str(params.queryParams.get("include_inactive", "")).lower() == "true"


def list(params: Params) -> PaginatedResult:
    page, page_size = parse_pagination(params)
    rows, metadata = location_db.list_locations(page, page_size, include_inactive=_include_inactive(params))
    return PaginatedResult([Location(**row) for row in rows], metadata)


def get(params: Params) -> Location:
    location_id = params.pathParams.get("location_id")
    row = location_db.get_location(location_id)
    return Location(**row)


def add(params: Params) -> Location:
    body = params.body or {}
    row = location_db.create_location(body)
    return Location(**row)


def edit(params: Params) -> Location:
    location_id = params.pathParams.get("location_id")
    body = params.body or {}
    row = location_db.update_location(location_id, body)
    return Location(**row)


def delete(params: Params) -> Location:
    location_id = params.pathParams.get("location_id")
    row = location_db.delete_location(location_id)
    return Location(**row)
