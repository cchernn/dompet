from ..lib.params import Params
from ..models.category_search import CategorySearchResult
from ..db import category_search as category_search_db
from ..utils.pagination import PaginatedResult, parse_pagination

MAX_SEARCH_PAGE_SIZE = 1000


def search(params: Params) -> PaginatedResult:
    page, page_size = parse_pagination(params, max_page_size=MAX_SEARCH_PAGE_SIZE)
    q = params.queryParams or {}
    rows, metadata = category_search_db.search_categories(params.user, page, page_size, q=q.get("q"))
    return PaginatedResult([CategorySearchResult(**row) for row in rows], metadata)
