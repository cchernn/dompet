from ..lib.exceptions import InvalidDataException
from ..utils.db import run_atomic


def _require_owned_transaction(cursor, user_id, transaction_id) -> None:
    cursor.execute(
        "SELECT 1 FROM dompet.transactions WHERE id = %s AND user_id = %s",
        (str(transaction_id), str(user_id)),
    )
    if not cursor.fetchone():
        raise InvalidDataException(ValueError(f"Transaction not found or not owned by user: {transaction_id}"))


def list_transaction_tags(user_id, transaction_id) -> list[dict]:
    def work(cursor):
        _require_owned_transaction(cursor, user_id, transaction_id)
        cursor.execute(
            """
            SELECT t.* FROM dompet.transaction_tags tt
            JOIN dompet.tags t ON t.id = tt.tag_id
            WHERE tt.transaction_id = %s
            ORDER BY t.name
            """,
            (str(transaction_id),),
        )
        return cursor.fetchall()

    return run_atomic(work)


def link_tag(user_id, transaction_id, tag_id) -> dict:
    def work(cursor):
        _require_owned_transaction(cursor, user_id, transaction_id)

        cursor.execute(
            "SELECT 1 FROM dompet.tags WHERE id = %s AND user_id = %s AND is_active = TRUE",
            (str(tag_id), str(user_id)),
        )
        if not cursor.fetchone():
            raise InvalidDataException(ValueError(f"Tag not found, inactive, or not owned by user: {tag_id}"))

        cursor.execute(
            """
            INSERT INTO dompet.transaction_tags (transaction_id, tag_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
            """,
            (str(transaction_id), str(tag_id)),
        )
        cursor.execute(
            """
            SELECT transaction_id, tag_id, created_at FROM dompet.transaction_tags
            WHERE transaction_id = %s AND tag_id = %s
            """,
            (str(transaction_id), str(tag_id)),
        )
        return cursor.fetchone()

    return run_atomic(work)


def unlink_tag(user_id, transaction_id, tag_id) -> None:
    def work(cursor):
        _require_owned_transaction(cursor, user_id, transaction_id)
        cursor.execute(
            "DELETE FROM dompet.transaction_tags WHERE transaction_id = %s AND tag_id = %s RETURNING transaction_id",
            (str(transaction_id), str(tag_id)),
        )
        if not cursor.fetchone():
            raise InvalidDataException(ValueError("Link not found"))

    return run_atomic(work)
