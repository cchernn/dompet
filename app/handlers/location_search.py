from ..lib.params import Params
from ..models.location_search import LocationSearchResult
from ..db import location_search as location_search_db
from ..utils.pagination import PaginatedResult, parse_pagination


def search(params: Params) -> PaginatedResult:
    # No raised page-size ceiling here (unlike accounts/categories/tags/
    # budgets) -- locations are meant to be typeahead-searched, not
    # fetched in full, since they can grow into the thousands.
    page, page_size = parse_pagination(params)
    q = params.queryParams or {}
    rows, metadata = location_search_db.search_locations(params.user, page, page_size, q=q.get("q"))
    return PaginatedResult([LocationSearchResult(**row) for row in rows], metadata)
