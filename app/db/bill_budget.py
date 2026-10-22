from ..lib.exceptions import NotFoundException
from ..utils.db import run_atomic, paginate


def _require_owned_bill(cursor, user_id, bill_id) -> None:
    cursor.execute(
        "SELECT 1 FROM dompet.bills WHERE id = %s AND user_id = %s",
        (str(bill_id), str(user_id)),
    )
    if not cursor.fetchone():
        raise NotFoundException(ValueError(f"Bill not found or not owned by user: {bill_id}"))


def list_bill_budgets(user_id, bill_id, page: int, page_size: int) -> tuple[list[dict], dict]:
    def work(cursor):
        _require_owned_bill(cursor, user_id, bill_id)
        query = """
            SELECT b.* FROM dompet.bill_budgets bb
            JOIN dompet.budgets b ON b.id = bb.budget_id
            WHERE bb.bill_id = %s
            ORDER BY b.name
        """
        return paginate(cursor, query, [str(bill_id)], page, page_size)

    return run_atomic(work, user_id=user_id)


def list_budget_bills(user_id, budget_id, page: int, page_size: int) -> tuple[list[dict], dict]:
    """The reverse direction of list_bill_budgets: a budget's bills, not a
    bill's budgets. Returns every linked bill regardless of which member
    owns it -- same as list_budget_transactions, a shared budget shows the
    group's combined bills, not just the caller's own."""
    def work(cursor):
        cursor.execute(
            "SELECT 1 FROM dompet.budget_members WHERE budget_id = %s AND user_id = %s",
            (str(budget_id), str(user_id)),
        )
        if not cursor.fetchone():
            raise NotFoundException(ValueError(f"Budget not found or not accessible by user: {budget_id}"))

        query = """
            SELECT bl.* FROM dompet.bill_budgets bb
            JOIN dompet.bills bl ON bl.id = bb.bill_id
            WHERE bb.budget_id = %s
            ORDER BY bl.due_date ASC
        """
        return paginate(cursor, query, [str(budget_id)], page, page_size)

    return run_atomic(work, user_id=user_id)


def link_budget(user_id, bill_id, budget_id) -> dict:
    def work(cursor):
        _require_owned_bill(cursor, user_id, bill_id)

        cursor.execute(
            """
            SELECT 1 FROM dompet.budgets b
            JOIN dompet.budget_members bm ON bm.budget_id = b.id
            WHERE b.id = %s AND b.is_active = TRUE AND bm.user_id = %s
            """,
            (str(budget_id), str(user_id)),
        )
        if not cursor.fetchone():
            raise NotFoundException(ValueError(f"Budget not found, inactive, or not accessible by user: {budget_id}"))

        cursor.execute("SELECT series_id FROM dompet.bills WHERE id = %s", (str(bill_id),))
        series_id = cursor.fetchone()["series_id"]

        if series_id:
            # Recurring: link every occurrence in the series, not just the
            # one this call was made on, so the whole recurring bill --
            # past and future occurrences alike -- is visible to the
            # budget. New occurrences generated later inherit this via
            # bill.py's _generate_due_occurrences.
            cursor.execute(
                """
                INSERT INTO dompet.bill_budgets (bill_id, budget_id)
                SELECT id, %s FROM dompet.bills WHERE series_id = %s AND user_id = %s
                ON CONFLICT DO NOTHING
                """,
                (str(budget_id), str(series_id), str(user_id)),
            )
        else:
            cursor.execute(
                """
                INSERT INTO dompet.bill_budgets (bill_id, budget_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
                """,
                (str(bill_id), str(budget_id)),
            )

        cursor.execute(
            """
            SELECT bill_id, budget_id, created_at FROM dompet.bill_budgets
            WHERE bill_id = %s AND budget_id = %s
            """,
            (str(bill_id), str(budget_id)),
        )
        return cursor.fetchone()

    return run_atomic(work, user_id=user_id)


def unlink_budget(user_id, bill_id, budget_id) -> None:
    def work(cursor):
        _require_owned_bill(cursor, user_id, bill_id)
        cursor.execute(
            "DELETE FROM dompet.bill_budgets WHERE bill_id = %s AND budget_id = %s RETURNING bill_id",
            (str(bill_id), str(budget_id)),
        )
        if not cursor.fetchone():
            raise NotFoundException(ValueError("Link not found"))

        cursor.execute("SELECT series_id FROM dompet.bills WHERE id = %s", (str(bill_id),))
        series_id = cursor.fetchone()["series_id"]
        if series_id:
            # Symmetric with link_budget's fan-out: unlinking one occurrence
            # unlinks the whole series from this budget.
            cursor.execute(
                """
                DELETE FROM dompet.bill_budgets
                WHERE budget_id = %s
                  AND bill_id IN (SELECT id FROM dompet.bills WHERE series_id = %s AND user_id = %s)
                """,
                (str(budget_id), str(series_id), str(user_id)),
            )

    return run_atomic(work, user_id=user_id)
