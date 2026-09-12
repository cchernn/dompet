import uuid

from ..lib.exceptions import InvalidDataException
from ..utils.db import run_atomic


def list_attachments(user_id, include_inactive: bool = False) -> list[dict]:
    def work(cursor):
        query = "SELECT * FROM dompet.attachments WHERE user_id = %s"
        params = [str(user_id)]
        if not include_inactive:
            query += " AND is_active = TRUE"
        query += " ORDER BY created_at DESC"
        cursor.execute(query, params)
        return cursor.fetchall()

    return run_atomic(work)


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

    return run_atomic(work)


def create_attachment_record(user_id, filename: str, content_type: str = None, size_bytes: int = None) -> dict:
    if not filename:
        raise InvalidDataException(ValueError("filename is required"))

    attachment_id = uuid.uuid4()
    storage_key = f"attachments/{user_id}/{attachment_id}/{filename}"

    def work(cursor):
        cursor.execute(
            """
            INSERT INTO dompet.attachments (id, user_id, filename, content_type, size_bytes, storage_key)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (str(attachment_id), str(user_id), filename, content_type, size_bytes, storage_key),
        )
        return cursor.fetchone()

    return run_atomic(work)


def delete_attachment(user_id, attachment_id) -> dict:
    def work(cursor):
        cursor.execute(
            "DELETE FROM dompet.attachments WHERE id = %s AND user_id = %s RETURNING *",
            (str(attachment_id), str(user_id)),
        )
        row = cursor.fetchone()
        if not row:
            raise InvalidDataException(ValueError(f"Attachment not found or not owned by user: {attachment_id}"))
        return row

    return run_atomic(work)
