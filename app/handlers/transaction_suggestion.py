from ..lib.params import Params
from ..models.transaction_suggestion import TransactionSuggestion
from ..db import transaction_suggestion as transaction_suggestion_db
from ..utils.pagination import PaginatedResult, parse_pagination


def search(params: Params) -> PaginatedResult:
    page, page_size = parse_pagination(params)
    q = params.queryParams or {}
    rows, metadata = transaction_suggestion_db.search_suggestions(
        params.user, page, page_size,
        q=q.get("q"), transaction_type=q.get("type"),
        min_uses=q.get("min_uses"), tz_offset=q.get("tz_offset"),
    )
    return PaginatedResult([TransactionSuggestion(**row) for row in rows], metadata)
