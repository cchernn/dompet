from ..lib.exceptions import InvalidDataException
from ..utils.db import run_atomic


def _require_owner(cursor, user_id, budget_id) -> dict:
    cursor.execute(
        "SELECT * FROM dompet.budgets WHERE id = %s AND user_id = %s",
        (str(budget_id), str(user_id)),
    )
    budget = cursor.fetchone()
    if not budget:
        raise InvalidDataException(ValueError(f"Budget not found or not owned by user: {budget_id}"))
    return budget


def list_members(user_id, budget_id) -> list[dict]:
    def work(cursor):
        cursor.execute(
            "SELECT 1 FROM dompet.budget_members WHERE budget_id = %s AND user_id = %s",
            (str(budget_id), str(user_id)),
        )
        if not cursor.fetchone():
            raise InvalidDataException(ValueError(f"Budget not found or not accessible by user: {budget_id}"))

        cursor.execute(
            "SELECT budget_id, user_id, created_at FROM dompet.budget_members WHERE budget_id = %s ORDER BY created_at",
            (str(budget_id),),
        )
        return cursor.fetchall()

    return run_atomic(work)


def add_member(user_id, budget_id, member_user_id) -> dict:
    def work(cursor):
        _require_owner(cursor, user_id, budget_id)

        cursor.execute(
            """
            INSERT INTO dompet.budget_members (budget_id, user_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
            """,
            (str(budget_id), str(member_user_id)),
        )
        cursor.execute(
            "SELECT budget_id, user_id, created_at FROM dompet.budget_members WHERE budget_id = %s AND user_id = %s",
            (str(budget_id), str(member_user_id)),
        )
        return cursor.fetchone()

    return run_atomic(work)


def remove_member(user_id, budget_id, member_user_id) -> None:
    def work(cursor):
        budget = _require_owner(cursor, user_id, budget_id)
        if str(budget["user_id"]) == str(member_user_id):
            raise InvalidDataException(ValueError("Cannot remove the budget owner from its own membership"))

        cursor.execute(
            "DELETE FROM dompet.budget_members WHERE budget_id = %s AND user_id = %s RETURNING budget_id",
            (str(budget_id), str(member_user_id)),
        )
        if not cursor.fetchone():
            raise InvalidDataException(ValueError("Membership not found"))

    return run_atomic(work)
