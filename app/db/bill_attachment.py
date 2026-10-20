from ..lib.exceptions import NotFoundException
from ..utils.db import run_atomic, paginate


def _require_owned_bill(cursor, user_id, bill_id) -> None:
    cursor.execute(
        "SELECT 1 FROM dompet.bills WHERE id = %s AND user_id = %s",
        (str(bill_id), str(user_id)),
    )
    if not cursor.fetchone():
        raise NotFoundException(ValueError(f"Bill not found: {bill_id}"))


def list_bill_attachments(user_id, bill_id, page: int, page_size: int) -> tuple[list[dict], dict]:
    def work(cursor):
        _require_owned_bill(cursor, user_id, bill_id)
        query = """
            SELECT a.* FROM dompet.bill_attachments ba
            JOIN dompet.attachments a ON a.id = ba.attachment_id
            WHERE ba.bill_id = %s
            ORDER BY a.created_at DESC
        """
        return paginate(cursor, query, [str(bill_id)], page, page_size)

    return run_atomic(work, user_id=user_id)


def link_attachment(user_id, bill_id, attachment_id) -> dict:
    def work(cursor):
        _require_owned_bill(cursor, user_id, bill_id)

        cursor.execute(
            "SELECT 1 FROM dompet.attachments WHERE id = %s AND user_id = %s AND is_active = TRUE",
            (str(attachment_id), str(user_id)),
        )
        if not cursor.fetchone():
            raise NotFoundException(ValueError(f"Attachment not found, inactive, or not owned by user: {attachment_id}"))

        cursor.execute(
            """
            INSERT INTO dompet.bill_attachments (bill_id, attachment_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
            """,
            (str(bill_id), str(attachment_id)),
        )
        cursor.execute(
            """
            SELECT bill_id, attachment_id, created_at FROM dompet.bill_attachments
            WHERE bill_id = %s AND attachment_id = %s
            """,
            (str(bill_id), str(attachment_id)),
        )
        return cursor.fetchone()

    return run_atomic(work, user_id=user_id)


def unlink_attachment(user_id, bill_id, attachment_id) -> None:
    def work(cursor):
        _require_owned_bill(cursor, user_id, bill_id)
        cursor.execute(
            "DELETE FROM dompet.bill_attachments WHERE bill_id = %s AND attachment_id = %s RETURNING bill_id",
            (str(bill_id), str(attachment_id)),
        )
        if not cursor.fetchone():
            raise NotFoundException(ValueError("Link not found"))

    return run_atomic(work, user_id=user_id)
