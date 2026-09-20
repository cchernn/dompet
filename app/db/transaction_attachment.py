from ..lib.exceptions import InvalidDataException
from ..utils.db import run_atomic, paginate


def _require_owned_transaction(cursor, user_id, transaction_id) -> None:
    cursor.execute(
        "SELECT 1 FROM dompet.transactions WHERE id = %s AND user_id = %s",
        (str(transaction_id), str(user_id)),
    )
    if not cursor.fetchone():
        raise InvalidDataException(ValueError(f"Transaction not found or not owned by user: {transaction_id}"))


def list_transaction_attachments(user_id, transaction_id, page: int, page_size: int) -> tuple[list[dict], dict]:
    def work(cursor):
        _require_owned_transaction(cursor, user_id, transaction_id)
        query = """
            SELECT a.* FROM dompet.transaction_attachments ta
            JOIN dompet.attachments a ON a.id = ta.attachment_id
            WHERE ta.transaction_id = %s
            ORDER BY a.created_at DESC
        """
        return paginate(cursor, query, [str(transaction_id)], page, page_size)

    return run_atomic(work, user_id=user_id)


def link_attachment(user_id, transaction_id, attachment_id) -> dict:
    def work(cursor):
        _require_owned_transaction(cursor, user_id, transaction_id)

        cursor.execute(
            "SELECT 1 FROM dompet.attachments WHERE id = %s AND user_id = %s AND is_active = TRUE",
            (str(attachment_id), str(user_id)),
        )
        if not cursor.fetchone():
            raise InvalidDataException(ValueError(f"Attachment not found, inactive, or not owned by user: {attachment_id}"))

        cursor.execute(
            """
            INSERT INTO dompet.transaction_attachments (transaction_id, attachment_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
            """,
            (str(transaction_id), str(attachment_id)),
        )
        cursor.execute(
            """
            SELECT transaction_id, attachment_id, created_at FROM dompet.transaction_attachments
            WHERE transaction_id = %s AND attachment_id = %s
            """,
            (str(transaction_id), str(attachment_id)),
        )
        return cursor.fetchone()

    return run_atomic(work, user_id=user_id)


def unlink_attachment(user_id, transaction_id, attachment_id) -> None:
    def work(cursor):
        _require_owned_transaction(cursor, user_id, transaction_id)
        cursor.execute(
            "DELETE FROM dompet.transaction_attachments WHERE transaction_id = %s AND attachment_id = %s RETURNING transaction_id",
            (str(transaction_id), str(attachment_id)),
        )
        if not cursor.fetchone():
            raise InvalidDataException(ValueError("Link not found"))

    return run_atomic(work, user_id=user_id)
