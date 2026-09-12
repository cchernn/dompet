from ..lib.params import Params
from ..models.location import Location
from ..db import location as location_db


def _include_inactive(params: Params) -> bool:
    if not params.queryParams:
        return False
    return str(params.queryParams.get("include_inactive", "")).lower() == "true"


def list(params: Params) -> list[Location]:
    rows = location_db.list_locations(include_inactive=_include_inactive(params))
    return [Location(**row) for row in rows]


def get(params: Params) -> Location:
    location_id = params.pathParams.get("location_id")
    row = location_db.get_location(location_id)
    return Location(**row)


def add(params: Params) -> Location:
    body = params.body or {}
    row = location_db.create_location(body)
    return Location(**row)
