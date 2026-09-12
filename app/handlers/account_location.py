from ..lib.params import Params
from ..lib.exceptions import InvalidDataException
from ..models.location import Location
from ..models.account_location import AccountLocationLink
from ..db import account_location as account_location_db


def list(params: Params) -> list[Location]:
    account_id = params.pathParams.get("account_id")
    rows = account_location_db.list_account_locations(params.user, account_id)
    return [Location(**row) for row in rows]


def add(params: Params) -> AccountLocationLink:
    account_id = params.pathParams.get("account_id")
    body = params.body or {}
    location_id = body.get("location_id")
    if not location_id:
        raise InvalidDataException(ValueError("location_id is required in the request body"))
    row = account_location_db.link_location(params.user, account_id, location_id)
    return AccountLocationLink(**row)


def delete(params: Params) -> dict:
    account_id = params.pathParams.get("account_id")
    location_id = params.pathParams.get("location_id")
    account_location_db.unlink_location(params.user, account_id, location_id)
    return {"unlinked": True}
