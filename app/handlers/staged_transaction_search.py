from ..lib.params import Params
from ..models.staged_transaction_search import StagedTransactionSearchResult
from ..db import staged_transaction_search as staged_transaction_search_db
from ..utils.pagination import PaginatedResult, parse_pagination

MAX_SEARCH_PAGE_SIZE = 1000


def _parse_bool(value) -> bool:
    if value is None:
        return None
    return str(value).lower() == "true"


def search(params: Params) -> PaginatedResult:
    page, page_size = parse_pagination(params, max_page_size=MAX_SEARCH_PAGE_SIZE)
    q = params.queryParams or {}
    rows, metadata = staged_transaction_search_db.search_staged(
        params.user, page, page_size,
        q=q.get("q"), status=q.get("status", "draft"), transaction_type=q.get("type"),
        origin=q.get("origin"), is_complete=_parse_bool(q.get("is_complete")),
        account_id=q.get("account_id"),
    )
    return PaginatedResult([StagedTransactionSearchResult(**row) for row in rows], metadata)
