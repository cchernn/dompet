from ..lib.params import Params
from ..models.attachment_search import AttachmentSearchResult
from ..db import attachment_search as attachment_search_db
from ..utils.pagination import PaginatedResult, parse_pagination


MAX_SEARCH_PAGE_SIZE = 1000


def search(params: Params) -> PaginatedResult:
    page, page_size = parse_pagination(params, max_page_size=MAX_SEARCH_PAGE_SIZE)
    q = params.queryParams or {}
    rows, metadata = attachment_search_db.search_attachments(params.user, page, page_size, q=q.get("q"))
    return PaginatedResult([AttachmentSearchResult(**row) for row in rows], metadata)
