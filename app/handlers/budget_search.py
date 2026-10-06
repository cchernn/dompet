from ..lib.params import Params
from ..models.budget_search import BudgetSearchResult
from ..db import budget_search as budget_search_db
from ..utils.pagination import PaginatedResult, parse_pagination

MAX_SEARCH_PAGE_SIZE = 1000


def search(params: Params) -> PaginatedResult:
    page, page_size = parse_pagination(params, max_page_size=MAX_SEARCH_PAGE_SIZE)
    q = params.queryParams or {}
    rows, metadata = budget_search_db.search_budgets(params.user, page, page_size, q=q.get("q"))
    return PaginatedResult([BudgetSearchResult(**row) for row in rows], metadata)
