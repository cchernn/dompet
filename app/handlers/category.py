from ..lib.params import Params
from ..models.category import Category
from ..db import category as category_db


def _include_inactive(params: Params) -> bool:
    if not params.queryParams:
        return False
    return str(params.queryParams.get("include_inactive", "")).lower() == "true"


def list(params: Params) -> list[Category]:
    rows = category_db.list_categories(params.user, include_inactive=_include_inactive(params))
    return [Category(**row) for row in rows]


def add(params: Params) -> Category:
    body = params.body or {}
    row = category_db.create_category(params.user, body)
    return Category(**row)
