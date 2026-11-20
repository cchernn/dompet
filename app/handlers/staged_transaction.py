from ..lib.params import Params
from ..models.staged_transaction import StagedTransaction
from ..models.transaction import Transaction
from ..db import staged_transaction as staged_transaction_db
from ..utils.pagination import PaginatedResult, parse_pagination


def list(params: Params) -> PaginatedResult:
    page, page_size = parse_pagination(params)
    status = (params.queryParams or {}).get("status", "draft")
    rows, metadata = staged_transaction_db.list_staged(
        params.user, page, page_size, status=None if status == "all" else status
    )
    return PaginatedResult([StagedTransaction(**row) for row in rows], metadata)


def get(params: Params) -> StagedTransaction:
    staged_id = params.pathParams.get("staged_id")
    row = staged_transaction_db.get_staged(params.user, staged_id)
    return StagedTransaction(**row)


def add(params: Params) -> StagedTransaction:
    body = params.body or {}
    row = staged_transaction_db.create_staged(params.user, body)
    return StagedTransaction(**row)


def edit(params: Params) -> StagedTransaction:
    staged_id = params.pathParams.get("staged_id")
    body = params.body or {}
    row = staged_transaction_db.update_staged(params.user, staged_id, body)
    return StagedTransaction(**row)


def delete(params: Params) -> StagedTransaction:
    staged_id = params.pathParams.get("staged_id")
    row = staged_transaction_db.discard_staged(params.user, staged_id)
    return StagedTransaction(**row)


def approve(params: Params) -> Transaction:
    staged_id = params.pathParams.get("staged_id")
    row = staged_transaction_db.approve_staged(params.user, staged_id, params.body or {})
    return Transaction(**row)
