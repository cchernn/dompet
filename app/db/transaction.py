from ..lib.exceptions import InvalidDataException
from ..utils.db import run_atomic


def list_transactions(user_id, include_inactive: bool = False) -> list[dict]:
    def work(cursor):
        query = "SELECT * FROM dompet.transactions WHERE user_id = %s"
        params = [str(user_id)]
        if not include_inactive:
            query += " AND is_active = TRUE"
        query += " ORDER BY date DESC, created_at DESC"
        cursor.execute(query, params)
        return cursor.fetchall()

    return run_atomic(work)


def get_transaction(user_id, transaction_id) -> dict:
    def work(cursor):
        cursor.execute(
            "SELECT * FROM dompet.transactions WHERE id = %s AND user_id = %s",
            (str(transaction_id), str(user_id)),
        )
        row = cursor.fetchone()
        if not row:
            raise InvalidDataException(ValueError(f"Transaction not found: {transaction_id}"))
        return row

    return run_atomic(work)
