from ..lib.params import Params
from ..lib.exceptions import InvalidDataException
from ..models.attachment import Attachment
from ..db import attachment as attachment_db
from ..utils import s3


def _to_attachment(row: dict) -> Attachment:
    row = dict(row)
    storage_key = row.pop("storage_key")
    row["download_url"] = s3.generate_download_url(storage_key)
    return Attachment(**row)


def _include_inactive(params: Params) -> bool:
    if not params.queryParams:
        return False
    return str(params.queryParams.get("include_inactive", "")).lower() == "true"


def list(params: Params) -> list[Attachment]:
    rows = attachment_db.list_attachments(params.user, include_inactive=_include_inactive(params))
    return [_to_attachment(row) for row in rows]


def get(params: Params) -> Attachment:
    attachment_id = params.pathParams.get("attachment_id")
    row = attachment_db.get_attachment(params.user, attachment_id)
    return _to_attachment(row)


def add(params: Params) -> dict:
    body = params.body or {}
    filename = body.get("filename")
    if not filename:
        raise InvalidDataException(ValueError("filename is required in the request body"))
    content_type = body.get("content_type")
    size_bytes = body.get("size_bytes")

    row = attachment_db.create_attachment_record(params.user, filename, content_type, size_bytes)
    storage_key = row["storage_key"]
    upload_url = s3.generate_upload_url(storage_key, content_type)
    return {
        "attachment": _to_attachment(row),
        "upload_url": upload_url,
    }


def edit(params: Params) -> Attachment:
    attachment_id = params.pathParams.get("attachment_id")
    body = params.body or {}
    row = attachment_db.update_attachment(params.user, attachment_id, body)
    return _to_attachment(row)


def delete(params: Params) -> dict:
    attachment_id = params.pathParams.get("attachment_id")
    row = attachment_db.delete_attachment(params.user, attachment_id)
    s3.delete_object(row["storage_key"])
    return {"deleted": True}
