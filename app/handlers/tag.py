from ..lib.params import Params
from ..models.tag import Tag
from ..db import tag as tag_db
from ..utils.pagination import PaginatedResult, parse_pagination


def _include_inactive(params: Params) -> bool:
    if not params.queryParams:
        return False
    return str(params.queryParams.get("include_inactive", "")).lower() == "true"


def list(params: Params) -> PaginatedResult:
    page, page_size = parse_pagination(params)
    rows, metadata = tag_db.list_tags(params.user, page, page_size, include_inactive=_include_inactive(params))
    return PaginatedResult([Tag(**row) for row in rows], metadata)


def add(params: Params) -> Tag:
    body = params.body or {}
    row = tag_db.create_tag(params.user, body)
    return Tag(**row)


def edit(params: Params) -> Tag:
    tag_id = params.pathParams.get("tag_id")
    body = params.body or {}
    row = tag_db.update_tag(params.user, tag_id, body)
    return Tag(**row)


def delete(params: Params) -> Tag:
    tag_id = params.pathParams.get("tag_id")
    row = tag_db.delete_tag(params.user, tag_id)
    return Tag(**row)
