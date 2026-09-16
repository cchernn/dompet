from ..lib.exceptions import InvalidDataException
from ..utils.db import run_atomic

UPDATABLE_FIELDS = ("name",)


def list_budgets(user_id, include_inactive: bool = False) -> list[dict]:
    def work(cursor):
        query = """
            SELECT b.* FROM dompet.budgets b
            JOIN dompet.budget_members bm ON bm.budget_id = b.id
            WHERE bm.user_id = %s
        """
        params = [str(user_id)]
        if not include_inactive:
            query += " AND b.is_active = TRUE"
        query += " ORDER BY b.name"
        cursor.execute(query, params)
        return cursor.fetchall()

    return run_atomic(work)


def get_budget(user_id, budget_id) -> dict:
    def work(cursor):
        cursor.execute(
            """
            SELECT b.* FROM dompet.budgets b
            JOIN dompet.budget_members bm ON bm.budget_id = b.id
            WHERE b.id = %s AND bm.user_id = %s
            """,
            (str(budget_id), str(user_id)),
        )
        row = cursor.fetchone()
        if not row:
            raise InvalidDataException(ValueError(f"Budget not found or not accessible by user: {budget_id}"))
        return row

    return run_atomic(work)


def create_budget(user_id, body: dict) -> dict:
    name = body.get("name")
    if not name:
        raise InvalidDataException(ValueError("name is required"))

    def work(cursor):
        cursor.execute(
            "SELECT * FROM dompet.budgets WHERE user_id = %s AND LOWER(name) = LOWER(%s)",
            (str(user_id), name),
        )
        existing = cursor.fetchone()
        if existing:
            row = existing
        else:
            cursor.execute(
                "INSERT INTO dompet.budgets (user_id, name) VALUES (%s, %s) RETURNING *",
                (str(user_id), name),
            )
            row = cursor.fetchone()

        cursor.execute(
            """
            INSERT INTO dompet.budget_members (budget_id, user_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
            """,
            (str(row["id"]), str(user_id)),
        )
        return row

    return run_atomic(work)


def update_budget(user_id, budget_id, body: dict) -> dict:
    """Owner-only, matching budget_member._require_owner -- editing/deleting
    a shared budget is not something a plain member should be able to do."""
    patch = {k: v for k, v in body.items() if k in UPDATABLE_FIELDS}
    if not patch:
        raise InvalidDataException(ValueError("No updatable fields provided"))

    def work(cursor):
        cursor.execute(
            "SELECT 1 FROM dompet.budgets WHERE id = %s AND user_id = %s FOR UPDATE",
            (str(budget_id), str(user_id)),
        )
        if not cursor.fetchone():
            raise InvalidDataException(ValueError(f"Budget not found or not owned by user: {budget_id}"))

        set_clause = ", ".join(f"{field} = %s" for field in patch)
        cursor.execute(
            f"UPDATE dompet.budgets SET {set_clause}, updated_at = NOW() WHERE id = %s AND user_id = %s RETURNING *",
            (*patch.values(), str(budget_id), str(user_id)),
        )
        return cursor.fetchone()

    return run_atomic(work)


def delete_budget(user_id, budget_id) -> dict:
    def work(cursor):
        cursor.execute(
            "UPDATE dompet.budgets SET is_active = FALSE, updated_at = NOW() WHERE id = %s AND user_id = %s RETURNING *",
            (str(budget_id), str(user_id)),
        )
        row = cursor.fetchone()
        if not row:
            raise InvalidDataException(ValueError(f"Budget not found or not owned by user: {budget_id}"))
        return row

    return run_atomic(work)
