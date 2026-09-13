from ..lib.exceptions import InvalidDataException
from ..utils.db import run_atomic


def _require_owned_transaction(cursor, user_id, transaction_id) -> None:
    cursor.execute(
        "SELECT 1 FROM dompet.transactions WHERE id = %s AND user_id = %s",
        (str(transaction_id), str(user_id)),
    )
    if not cursor.fetchone():
        raise InvalidDataException(ValueError(f"Transaction not found or not owned by user: {transaction_id}"))


def list_transaction_budgets(user_id, transaction_id) -> list[dict]:
    def work(cursor):
        _require_owned_transaction(cursor, user_id, transaction_id)
        cursor.execute(
            """
            SELECT b.* FROM dompet.transaction_budgets tb
            JOIN dompet.budgets b ON b.id = tb.budget_id
            WHERE tb.transaction_id = %s
            ORDER BY b.name
            """,
            (str(transaction_id),),
        )
        return cursor.fetchall()

    return run_atomic(work)


def link_budget(user_id, transaction_id, budget_id) -> dict:
    def work(cursor):
        _require_owned_transaction(cursor, user_id, transaction_id)

        cursor.execute(
            """
            SELECT 1 FROM dompet.budgets b
            JOIN dompet.budget_members bm ON bm.budget_id = b.id
            WHERE b.id = %s AND b.is_active = TRUE AND bm.user_id = %s
            """,
            (str(budget_id), str(user_id)),
        )
        if not cursor.fetchone():
            raise InvalidDataException(ValueError(f"Budget not found, inactive, or not accessible by user: {budget_id}"))

        cursor.execute(
            """
            INSERT INTO dompet.transaction_budgets (transaction_id, budget_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
            """,
            (str(transaction_id), str(budget_id)),
        )
        cursor.execute(
            """
            SELECT transaction_id, budget_id, created_at FROM dompet.transaction_budgets
            WHERE transaction_id = %s AND budget_id = %s
            """,
            (str(transaction_id), str(budget_id)),
        )
        return cursor.fetchone()

    return run_atomic(work)


def unlink_budget(user_id, transaction_id, budget_id) -> None:
    def work(cursor):
        _require_owned_transaction(cursor, user_id, transaction_id)
        cursor.execute(
            "DELETE FROM dompet.transaction_budgets WHERE transaction_id = %s AND budget_id = %s RETURNING transaction_id",
            (str(transaction_id), str(budget_id)),
        )
        if not cursor.fetchone():
            raise InvalidDataException(ValueError("Link not found"))

    return run_atomic(work)
