from ..lib.params import Params
from ..models.statement_search import StatementSearchResult
from ..db import statement_search as statement_search_db
from ..utils.pagination import PaginatedResult, parse_pagination

MAX_SEARCH_PAGE_SIZE = 1000


def _parse_bool(value) -> bool:
    if value is None:
        return None
    return str(value).lower() == "true"


def search(params: Params) -> PaginatedResult:
    page, page_size = parse_pagination(params, max_page_size=MAX_SEARCH_PAGE_SIZE)
    q = params.queryParams or {}
    rows, metadata = statement_search_db.search_statements(
        params.user, page, page_size,
        q=q.get("q"), account=q.get("account"), account_id=q.get("account_id"),
        is_recurring=_parse_bool(q.get("is_recurring")), status=q.get("status"),
        date_from=q.get("from"), date_to=q.get("to"),
    )
    return PaginatedResult([StatementSearchResult(**row) for row in rows], metadata)
