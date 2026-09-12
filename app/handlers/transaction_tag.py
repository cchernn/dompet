from ..lib.params import Params
from ..lib.exceptions import InvalidDataException
from ..models.tag import Tag
from ..models.transaction_tag import TransactionTagLink
from ..db import transaction_tag as transaction_tag_db


def list(params: Params) -> list[Tag]:
    transaction_id = params.pathParams.get("transaction_id")
    rows = transaction_tag_db.list_transaction_tags(params.user, transaction_id)
    return [Tag(**row) for row in rows]


def add(params: Params) -> TransactionTagLink:
    transaction_id = params.pathParams.get("transaction_id")
    body = params.body or {}
    tag_id = body.get("tag_id")
    if not tag_id:
        raise InvalidDataException(ValueError("tag_id is required in the request body"))
    row = transaction_tag_db.link_tag(params.user, transaction_id, tag_id)
    return TransactionTagLink(**row)


def delete(params: Params) -> dict:
    transaction_id = params.pathParams.get("transaction_id")
    tag_id = params.pathParams.get("tag_id")
    transaction_tag_db.unlink_tag(params.user, transaction_id, tag_id)
    return {"unlinked": True}
