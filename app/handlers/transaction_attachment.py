from ..lib.params import Params
from ..lib.exceptions import InvalidDataException
from ..models.transaction_attachment import TransactionAttachmentLink
from ..db import transaction_attachment as transaction_attachment_db
from .attachment import _to_attachment


def list(params: Params) -> list:
    transaction_id = params.pathParams.get("transaction_id")
    rows = transaction_attachment_db.list_transaction_attachments(params.user, transaction_id)
    return [_to_attachment(row) for row in rows]


def add(params: Params) -> TransactionAttachmentLink:
    transaction_id = params.pathParams.get("transaction_id")
    body = params.body or {}
    attachment_id = body.get("attachment_id")
    if not attachment_id:
        raise InvalidDataException(ValueError("attachment_id is required in the request body"))
    row = transaction_attachment_db.link_attachment(params.user, transaction_id, attachment_id)
    return TransactionAttachmentLink(**row)


def delete(params: Params) -> dict:
    transaction_id = params.pathParams.get("transaction_id")
    attachment_id = params.pathParams.get("attachment_id")
    transaction_attachment_db.unlink_attachment(params.user, transaction_id, attachment_id)
    return {"unlinked": True}
