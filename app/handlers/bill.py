from ..lib.params import Params
from ..models.bill import Bill
from ..db import bill as bill_db
from ..utils.pagination import PaginatedResult, parse_pagination


def _include_inactive(params: Params) -> bool:
    if not params.queryParams:
        return False
    return str(params.queryParams.get("include_inactive", "")).lower() == "true"


def list(params: Params) -> PaginatedResult:
    page, page_size = parse_pagination(params)
    rows, metadata = bill_db.list_bills(params.user, page, page_size, include_inactive=_include_inactive(params))
    return PaginatedResult([Bill(**row) for row in rows], metadata)


def get(params: Params) -> Bill:
    bill_id = params.pathParams.get("bill_id")
    row = bill_db.get_bill(params.user, bill_id)
    return Bill(**row)


def add(params: Params) -> Bill:
    body = params.body or {}
    row = bill_db.create_bill(params.user, body)
    return Bill(**row)


def edit(params: Params) -> Bill:
    bill_id = params.pathParams.get("bill_id")
    body = params.body or {}
    row = bill_db.update_bill(params.user, bill_id, body)
    return Bill(**row)


def delete(params: Params) -> Bill:
    bill_id = params.pathParams.get("bill_id")
    row = bill_db.deactivate_bill(params.user, bill_id)
    return Bill(**row)
