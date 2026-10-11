from ..lib.params import Params
from ..models.transaction_search import TransactionSearchResult
from ..db import transaction_search as transaction_search_db
from ..utils.pagination import PaginatedResult, parse_pagination
from ..utils.filters import parse_owner_filter


def search(params: Params) -> PaginatedResult:
    page, page_size = parse_pagination(params)
    q = params.queryParams or {}
    rows, metadata = transaction_search_db.search_transactions(
        params.user, page, page_size,
        date_from=q.get("from"), date_to=q.get("to"),
        category=q.get("category"), transaction_type=q.get("type"),
        source=q.get("source"), destination=q.get("destination"),
        tags=q.get("tags"), budgets=q.get("budgets"),
        source_location=q.get("source_location"), destination_location=q.get("destination_location"),
        owner=parse_owner_filter(q.get("user_id"), allow_null=False),
        q=q.get("q"),
    )
    results = []
    for row in rows:
        row = dict(row)
        row["tags"] = row["tags"] or []
        row["attachments"] = row["attachments"] or []
        row["budgets"] = row["budgets"] or []
        results.append(TransactionSearchResult(**row))
    return PaginatedResult(results, metadata)
