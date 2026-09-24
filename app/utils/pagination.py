from ..lib.params import Params

DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100


class PaginatedResult:
    """Returned by a list handler to carry pagination metadata alongside
    its items. app.main.main unpacks this into Response.data/metadata so
    every other handler can keep returning plain data untouched."""

    def __init__(self, items: list, metadata: dict):
        self.items = items
        self.metadata = metadata


def parse_pagination(params: Params) -> tuple[int, int]:
    query_params = params.queryParams or {}

    try:
        page = int(query_params.get("page", 1))
    except (TypeError, ValueError):
        page = 1
    page = max(1, page)

    try:
        page_size = int(query_params.get("page_size", DEFAULT_PAGE_SIZE))
    except (TypeError, ValueError):
        page_size = DEFAULT_PAGE_SIZE
    page_size = max(1, min(page_size, MAX_PAGE_SIZE))

    return page, page_size
