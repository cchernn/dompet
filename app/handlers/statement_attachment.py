from ..lib.params import Params
from ..lib.exceptions import InvalidDataException
from ..models.statement_attachment import StatementAttachmentLink
from ..db import statement_attachment as statement_attachment_db
from ..utils.pagination import PaginatedResult, parse_pagination
from .attachment import _to_attachment_summary


def list(params: Params) -> PaginatedResult:
    statement_id = params.pathParams.get("statement_id")
    page, page_size = parse_pagination(params)
    rows, metadata = statement_attachment_db.list_statement_attachments(params.user, statement_id, page, page_size)
    return PaginatedResult([_to_attachment_summary(row) for row in rows], metadata)


def add(params: Params) -> StatementAttachmentLink:
    statement_id = params.pathParams.get("statement_id")
    body = params.body or {}
    attachment_id = body.get("attachment_id")
    if not attachment_id:
        raise InvalidDataException(ValueError("attachment_id is required in the request body"))
    row = statement_attachment_db.link_attachment(params.user, statement_id, attachment_id)
    return StatementAttachmentLink(**row)


def delete(params: Params) -> dict:
    statement_id = params.pathParams.get("statement_id")
    attachment_id = params.pathParams.get("attachment_id")
    statement_attachment_db.unlink_attachment(params.user, statement_id, attachment_id)
    return {"unlinked": True}
