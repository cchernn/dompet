from ..lib.params import Params
from ..models.bill_payment import BillPayment
from ..db import bill_payment as bill_payment_db
from ..utils.pagination import PaginatedResult, parse_pagination


def list(params: Params) -> PaginatedResult:
    bill_id = params.pathParams.get("bill_id")
    page, page_size = parse_pagination(params)
    rows, metadata = bill_payment_db.list_payments(params.user, bill_id, page, page_size)
    return PaginatedResult([BillPayment(**row) for row in rows], metadata)


def add(params: Params) -> BillPayment:
    bill_id = params.pathParams.get("bill_id")
    body = params.body or {}
    row = bill_payment_db.create_payment(params.user, bill_id, body)
    return BillPayment(**row)


def delete(params: Params) -> dict:
    bill_id = params.pathParams.get("bill_id")
    payment_id = params.pathParams.get("payment_id")
    bill_payment_db.delete_payment(params.user, bill_id, payment_id)
    return {"deleted": True}
