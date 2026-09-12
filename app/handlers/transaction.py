from ..lib.params import Params
from ..lib.exceptions import InvalidDataException
from ..models.transaction import Transaction
from ..db import transaction as transaction_db
from ..db import transaction_operation


def _include_inactive(params: Params) -> bool:
    if not params.queryParams:
        return False
    return str(params.queryParams.get("include_inactive", "")).lower() == "true"


def list(params: Params) -> list[Transaction]:
    rows = transaction_db.list_transactions(params.user, include_inactive=_include_inactive(params))
    return [Transaction(**row) for row in rows]


def get(params: Params) -> Transaction:
    transaction_id = params.pathParams.get("transaction_id")
    row = transaction_db.get_transaction(params.user, transaction_id)
    return Transaction(**row)


def add(params: Params) -> Transaction:
    body = params.body or {}
    row = transaction_operation.create_transaction(params.user, body)
    return Transaction(**row)


def edit(params: Params) -> Transaction:
    transaction_id = params.pathParams.get("transaction_id")
    body = params.body or {}
    row = transaction_operation.update_transaction(params.user, transaction_id, body)
    return Transaction(**row)


def deactivate(params: Params) -> Transaction:
    transaction_id = params.pathParams.get("transaction_id")
    row = transaction_operation.deactivate_transaction(params.user, transaction_id)
    return Transaction(**row)


def reactivate(params: Params) -> Transaction:
    transaction_id = params.pathParams.get("transaction_id")
    row = transaction_operation.reactivate_transaction(params.user, transaction_id)
    return Transaction(**row)


def rollback(params: Params) -> Transaction:
    transaction_id = params.pathParams.get("transaction_id")
    body = params.body or {}
    target_operation_id = body.get("operation_id")
    if not target_operation_id:
        raise InvalidDataException(ValueError("operation_id is required in the request body"))
    row = transaction_operation.rollback_transaction(params.user, transaction_id, target_operation_id)
    return Transaction(**row)
