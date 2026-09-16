from ..lib.params import Params
from ..models.category import Category
from ..db import category as category_db
from ..utils.pagination import PaginatedResult, parse_pagination


def _include_inactive(params: Params) -> bool:
    if not params.queryParams:
        return False
    return str(params.queryParams.get("include_inactive", "")).lower() == "true"


def list(params: Params) -> PaginatedResult:
    page, page_size = parse_pagination(params)
    rows, metadata = category_db.list_categories(params.user, page, page_size, include_inactive=_include_inactive(params))
    return PaginatedResult([Category(**row) for row in rows], metadata)


def add(params: Params) -> Category:
    body = params.body or {}
    row = category_db.create_category(params.user, body)
    return Category(**row)


def edit(params: Params) -> Category:
    category_id = params.pathParams.get("category_id")
    body = params.body or {}
    row = category_db.update_category(params.user, category_id, body)
    return Category(**row)


def delete(params: Params) -> Category:
    category_id = params.pathParams.get("category_id")
    row = category_db.delete_category(params.user, category_id)
    return Category(**row)
