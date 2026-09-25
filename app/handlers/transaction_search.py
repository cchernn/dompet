from ..lib.params import Params
from ..models.transaction_search import TransactionSearchResult
from ..db import transaction_search as transaction_search_db
from ..utils.pagination import PaginatedResult, parse_pagination


def search(params: Params) -> PaginatedResult:
    page, page_size = parse_pagination(params)
    q = params.queryParams or {}
    rows, metadata = transaction_search_db.search_transactions(
        params.user, page, page_size,
        date_from=q.get("from"), date_to=q.get("to"),
        category=q.get("category"), type=q.get("type"),
    )
    results = []
    for row in rows:
        row = dict(row)
        row["tags"] = row["tags"].split("|") if row["tags"] else []
        row["attachments"] = row["attachments"].split("|") if row["attachments"] else []
        results.append(TransactionSearchResult(**row))
    return PaginatedResult(results, metadata)
