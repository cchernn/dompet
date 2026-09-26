import uuid

from psycopg2.extras import Json

from ..lib.exceptions import InvalidDataException
from ..utils.db import run_atomic, paginate
from .operations import row_to_dict, record_operation

UPDATABLE_FIELDS = ("filename", "content_type")


def list_attachments(user_id, page: int, page_size: int, include_inactive: bool = False) -> tuple[list[dict], dict]:
    def work(cursor):
        query = "SELECT * FROM dompet.attachments WHERE user_id = %s"
        params = [str(user_id)]
        if not include_inactive:
            query += " AND is_active = TRUE"
        query += " ORDER BY created_at DESC"
        return paginate(cursor, query, params, page, page_size)

    return run_atomic(work, user_id=user_id)


def get_attachment(user_id, attachment_id) -> dict:
    def work(cursor):
        cursor.execute(
            "SELECT * FROM dompet.attachments WHERE id = %s AND user_id = %s",
            (str(attachment_id), str(user_id)),
        )
        row = cursor.fetchone()
        if not row:
            raise InvalidDataException(ValueError(f"Attachment not found or not owned by user: {attachment_id}"))
        return row

    return run_atomic(work, user_id=user_id)


def create_attachment_record(
    user_id, filename: str, content_type: str = None, size_bytes: int = None, metadata: dict = None
) -> dict:
    if not filename:
        raise InvalidDataException(ValueError("filename is required"))

    attachment_id = uuid.uuid4()
    storage_key = f"attachments/{user_id}/{attachment_id}/{filename}"

    def work(cursor):
        cursor.execute(
            """
            INSERT INTO dompet.attachments (id, user_id, filename, content_type, size_bytes, storage_key, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (
                str(attachment_id),
                str(user_id),
                filename,
                content_type,
                size_bytes,
                storage_key,
                Json(metadata) if metadata is not None else None,
            ),
        )
        row = cursor.fetchone()
        record_operation(cursor, "attachment", row["id"], user_id, "CREATE", None, row_to_dict(row), metadata)
        return row

    return run_atomic(work, user_id=user_id)


def update_attachment(user_id, attachment_id, body: dict) -> dict:
    """Metadata-only rename (filename/content_type) -- the underlying S3
    object at storage_key is left untouched, so the presigned URLs
    generated from it keep working."""
    patch = {k: v for k, v in body.items() if k in UPDATABLE_FIELDS}
    if not patch:
        raise InvalidDataException(ValueError("No updatable fields provided"))

    def work(cursor):
        cursor.execute(
            "SELECT * FROM dompet.attachments WHERE id = %s AND user_id = %s FOR UPDATE",
            (str(attachment_id), str(user_id)),
        )
        before = cursor.fetchone()
        if not before:
            raise InvalidDataException(ValueError(f"Attachment not found or not owned by user: {attachment_id}"))

        set_clause = ", ".join(f"{field} = %s" for field in patch)
        cursor.execute(
            f"UPDATE dompet.attachments SET {set_clause}, updated_at = NOW() WHERE id = %s AND user_id = %s RETURNING *",
            (*patch.values(), str(attachment_id), str(user_id)),
        )
        after = cursor.fetchone()
        record_operation(cursor, "attachment", attachment_id, user_id, "UPDATE", row_to_dict(before), row_to_dict(after))
        return after

    return run_atomic(work, user_id=user_id)


def delete_attachment(user_id, attachment_id) -> dict:
    def work(cursor):
        cursor.execute(
            "DELETE FROM dompet.attachments WHERE id = %s AND user_id = %s RETURNING *",
            (str(attachment_id), str(user_id)),
        )
        row = cursor.fetchone()
        if not row:
            raise InvalidDataException(ValueError(f"Attachment not found or not owned by user: {attachment_id}"))
        record_operation(cursor, "attachment", attachment_id, user_id, "DELETE", row_to_dict(row), None)
        return row

    return run_atomic(work, user_id=user_id)
