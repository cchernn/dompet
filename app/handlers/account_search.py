from ..lib.params import Params
from ..models.account_search import AccountSearchResult
from ..db import account_search as account_search_db
from ..utils.pagination import PaginatedResult, parse_pagination

MAX_SEARCH_PAGE_SIZE = 1000


def search(params: Params) -> PaginatedResult:
    page, page_size = parse_pagination(params, max_page_size=MAX_SEARCH_PAGE_SIZE)
    q = params.queryParams or {}
    rows, metadata = account_search_db.search_accounts(params.user, page, page_size, q=q.get("q"))
    return PaginatedResult([AccountSearchResult(**row) for row in rows], metadata)
