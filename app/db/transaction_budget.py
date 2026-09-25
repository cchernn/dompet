from ..lib.exceptions import InvalidDataException
from ..utils.db import run_atomic, paginate


def _require_owned_transaction(cursor, user_id, transaction_id) -> None:
    cursor.execute(
        "SELECT 1 FROM dompet.transactions WHERE id = %s AND user_id = %s",
        (str(transaction_id), str(user_id)),
    )
    if not cursor.fetchone():
        raise InvalidDataException(ValueError(f"Transaction not found or not owned by user: {transaction_id}"))


def list_transaction_budgets(user_id, transaction_id, page: int, page_size: int) -> tuple[list[dict], dict]:
    def work(cursor):
        _require_owned_transaction(cursor, user_id, transaction_id)
        query = """
            SELECT b.* FROM dompet.transaction_budgets tb
            JOIN dompet.budgets b ON b.id = tb.budget_id
            WHERE tb.transaction_id = %s
            ORDER BY b.name
        """
        return paginate(cursor, query, [str(transaction_id)], page, page_size)

    return run_atomic(work, user_id=user_id)


def list_budget_transactions(user_id, budget_id, page: int, page_size: int) -> tuple[list[dict], dict]:
    """The reverse direction of list_transaction_budgets: a budget's
    transactions, not a transaction's budgets. Returns every linked
    transaction regardless of which member owns it -- a shared budget is
    meant to show the group's combined spending, not just the caller's own
    transactions."""
    def work(cursor):
        cursor.execute(
            "SELECT 1 FROM dompet.budget_members WHERE budget_id = %s AND user_id = %s",
            (str(budget_id), str(user_id)),
        )
        if not cursor.fetchone():
            raise InvalidDataException(ValueError(f"Budget not found or not accessible by user: {budget_id}"))

        query = """
            SELECT t.* FROM dompet.transaction_budgets tb
            JOIN dompet.transactions t ON t.id = tb.transaction_id
            WHERE tb.budget_id = %s
            ORDER BY t.datetime DESC, t.created_at DESC
        """
        return paginate(cursor, query, [str(budget_id)], page, page_size)

    return run_atomic(work, user_id=user_id)


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

    return run_atomic(work, user_id=user_id)


def unlink_budget(user_id, transaction_id, budget_id) -> None:
    def work(cursor):
        _require_owned_transaction(cursor, user_id, transaction_id)
        cursor.execute(
            "DELETE FROM dompet.transaction_budgets WHERE transaction_id = %s AND budget_id = %s RETURNING transaction_id",
            (str(transaction_id), str(budget_id)),
        )
        if not cursor.fetchone():
            raise InvalidDataException(ValueError("Link not found"))

    return run_atomic(work, user_id=user_id)
