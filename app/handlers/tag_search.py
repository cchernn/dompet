from ..lib.params import Params
from ..models.tag_search import TagSearchResult
from ..db import tag_search as tag_search_db
from ..utils.pagination import PaginatedResult, parse_pagination

MAX_SEARCH_PAGE_SIZE = 1000


def search(params: Params) -> PaginatedResult:
    page, page_size = parse_pagination(params, max_page_size=MAX_SEARCH_PAGE_SIZE)
    q = params.queryParams or {}
    rows, metadata = tag_search_db.search_tags(params.user, page, page_size, q=q.get("q"))
    return PaginatedResult([TagSearchResult(**row) for row in rows], metadata)
