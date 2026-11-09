from ..lib.params import Params
from ..lib.exceptions import InvalidDataException
from ..models.bill_attachment import BillAttachmentLink
from ..db import bill_attachment as bill_attachment_db
from ..utils.pagination import PaginatedResult, parse_pagination
from .attachment import _to_attachment_summary


def list(params: Params) -> PaginatedResult:
    bill_id = params.pathParams.get("bill_id")
    page, page_size = parse_pagination(params)
    rows, metadata = bill_attachment_db.list_bill_attachments(params.user, bill_id, page, page_size)
    return PaginatedResult([_to_attachment_summary(row) for row in rows], metadata)


def add(params: Params) -> BillAttachmentLink:
    bill_id = params.pathParams.get("bill_id")
    body = params.body or {}
    attachment_id = body.get("attachment_id")
    if not attachment_id:
        raise InvalidDataException(ValueError("attachment_id is required in the request body"))
    row = bill_attachment_db.link_attachment(params.user, bill_id, attachment_id)
    return BillAttachmentLink(**row)


def delete(params: Params) -> dict:
    bill_id = params.pathParams.get("bill_id")
    attachment_id = params.pathParams.get("attachment_id")
    bill_attachment_db.unlink_attachment(params.user, bill_id, attachment_id)
    return {"unlinked": True}
