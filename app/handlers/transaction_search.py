from ..lib.params import Params
from ..models.transaction_search import TransactionSearchResult
from ..db import transaction_search as transaction_search_db
from ..utils.pagination import PaginatedResult, parse_pagination


def search(params: Params) -> PaginatedResult:
    page, page_size = parse_pagination(params)
    q = params.queryParams or {}
    rows, metadata = transaction_search_db.search_transactions(params.user, page, page_size, q)
    results = []
    for row in rows:
        row = dict(row)
        row["tags"] = row["tags"] or []
        row["attachments"] = row["attachments"] or []
        row["budgets"] = row["budgets"] or []
        results.append(TransactionSearchResult(**row))
    return PaginatedResult(results, metadata)
