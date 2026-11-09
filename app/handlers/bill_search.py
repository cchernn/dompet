from ..lib.params import Params
from ..models.bill_search import BillSearchResult
from ..db import bill_search as bill_search_db
from ..utils.pagination import PaginatedResult, parse_pagination

MAX_SEARCH_PAGE_SIZE = 1000


def _parse_bool(value) -> bool:
    if value is None:
        return None
    return str(value).lower() == "true"


def search(params: Params) -> PaginatedResult:
    page, page_size = parse_pagination(params, max_page_size=MAX_SEARCH_PAGE_SIZE)
    q = params.queryParams or {}
    rows, metadata = bill_search_db.search_bills(
        params.user, page, page_size,
        q=q.get("q"), category=q.get("category"), account=q.get("account"),
        is_recurring=_parse_bool(q.get("is_recurring")), status=q.get("status"),
        date_from=q.get("from"), date_to=q.get("to"),
    )
    return PaginatedResult([BillSearchResult(**row) for row in rows], metadata)
