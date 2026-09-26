from ..lib.params import Params
from ..models.attachment_search import AttachmentSearchResult
from ..db import attachment_search as attachment_search_db
from ..utils.pagination import PaginatedResult, parse_pagination


def search(params: Params) -> PaginatedResult:
    # No raised page-size ceiling here either -- same typeahead reasoning
    # as locations.
    page, page_size = parse_pagination(params)
    q = params.queryParams or {}
    rows, metadata = attachment_search_db.search_attachments(params.user, page, page_size, q=q.get("q"))
    return PaginatedResult([AttachmentSearchResult(**row) for row in rows], metadata)
