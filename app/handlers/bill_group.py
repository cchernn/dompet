from ..lib.params import Params
from ..models.bill_group import BillGroup
from ..db import bill_group as bill_group_db
from ..utils.pagination import PaginatedResult, parse_pagination

MAX_SEARCH_PAGE_SIZE = 1000


def _parse_bool(value) -> bool:
    if value is None:
        return None
    return str(value).lower() == "true"


def search(params: Params) -> PaginatedResult:
    page, page_size = parse_pagination(params, max_page_size=MAX_SEARCH_PAGE_SIZE)
    q = params.queryParams or {}
    rows, metadata = bill_group_db.search_groups(
        params.user, page, page_size,
        q=q.get("q"), kind=q.get("kind"), category=q.get("category"), account=q.get("account"),
        is_overdue=_parse_bool(q.get("is_overdue")), include_paid=bool(_parse_bool(q.get("include_paid"))),
    )
    return PaginatedResult([BillGroup(**row) for row in rows], metadata)
