from ..lib.params import Params
from ..models.tag import Tag
from ..db import tag as tag_db


def _include_inactive(params: Params) -> bool:
    if not params.queryParams:
        return False
    return str(params.queryParams.get("include_inactive", "")).lower() == "true"


def list(params: Params) -> list[Tag]:
    rows = tag_db.list_tags(params.user, include_inactive=_include_inactive(params))
    return [Tag(**row) for row in rows]


def add(params: Params) -> Tag:
    body = params.body or {}
    row = tag_db.create_tag(params.user, body)
    return Tag(**row)
