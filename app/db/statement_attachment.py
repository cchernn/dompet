from ..lib.exceptions import NotFoundException
from ..utils.db import run_atomic, paginate


def _require_owned_statement(cursor, user_id, statement_id) -> None:
    cursor.execute(
        "SELECT 1 FROM dompet.statements WHERE id = %s AND user_id = %s",
        (str(statement_id), str(user_id)),
    )
    if not cursor.fetchone():
        raise NotFoundException(ValueError(f"Statement not found: {statement_id}"))


def list_statement_attachments(user_id, statement_id, page: int, page_size: int) -> tuple[list[dict], dict]:
    def work(cursor):
        _require_owned_statement(cursor, user_id, statement_id)
        query = """
            SELECT a.* FROM dompet.statement_attachments sa
            JOIN dompet.attachments a ON a.id = sa.attachment_id
            WHERE sa.statement_id = %s
            ORDER BY a.created_at DESC
        """
        return paginate(cursor, query, [str(statement_id)], page, page_size)

    return run_atomic(work, user_id=user_id)


def link_attachment(user_id, statement_id, attachment_id) -> dict:
    def work(cursor):
        _require_owned_statement(cursor, user_id, statement_id)

        cursor.execute(
            "SELECT 1 FROM dompet.attachments WHERE id = %s AND user_id = %s AND is_active = TRUE",
            (str(attachment_id), str(user_id)),
        )
        if not cursor.fetchone():
            raise NotFoundException(ValueError(f"Attachment not found, inactive, or not owned by user: {attachment_id}"))

        cursor.execute(
            """
            INSERT INTO dompet.statement_attachments (statement_id, attachment_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
            """,
            (str(statement_id), str(attachment_id)),
        )
        cursor.execute(
            """
            SELECT statement_id, attachment_id, created_at FROM dompet.statement_attachments
            WHERE statement_id = %s AND attachment_id = %s
            """,
            (str(statement_id), str(attachment_id)),
        )
        return cursor.fetchone()

    return run_atomic(work, user_id=user_id)


def unlink_attachment(user_id, statement_id, attachment_id) -> None:
    def work(cursor):
        _require_owned_statement(cursor, user_id, statement_id)
        cursor.execute(
            "DELETE FROM dompet.statement_attachments WHERE statement_id = %s AND attachment_id = %s RETURNING statement_id",
            (str(statement_id), str(attachment_id)),
        )
        if not cursor.fetchone():
            raise NotFoundException(ValueError("Link not found"))

    return run_atomic(work, user_id=user_id)
