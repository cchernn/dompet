from ..lib.exceptions import InvalidDataException, NotFoundException
from ..utils.db import run_atomic, paginate
from .user import find_by_username

MEMBER_SELECT = """
    SELECT bm.budget_id, bm.user_id, bm.created_at, u.username, u.display_name
    FROM dompet.budget_members bm
    LEFT JOIN dompet.vw_users_public u ON u.id = bm.user_id
"""


def _require_owner(cursor, user_id, budget_id) -> dict:
    cursor.execute(
        "SELECT * FROM dompet.budgets WHERE id = %s AND user_id = %s",
        (str(budget_id), str(user_id)),
    )
    budget = cursor.fetchone()
    if not budget:
        raise NotFoundException(ValueError(f"Budget not found or not owned by user: {budget_id}"))
    return budget


def list_members(user_id, budget_id, page: int, page_size: int) -> tuple[list[dict], dict]:
    def work(cursor):
        cursor.execute(
            "SELECT 1 FROM dompet.budget_members WHERE budget_id = %s AND user_id = %s",
            (str(budget_id), str(user_id)),
        )
        if not cursor.fetchone():
            raise NotFoundException(ValueError(f"Budget not found or not accessible by user: {budget_id}"))

        query = MEMBER_SELECT + " WHERE bm.budget_id = %s ORDER BY bm.created_at"
        return paginate(cursor, query, [str(budget_id)], page, page_size)

    return run_atomic(work, user_id=user_id)


def add_member(user_id, budget_id, username) -> dict:
    def work(cursor):
        _require_owner(cursor, user_id, budget_id)
        member_user_id = find_by_username(cursor, username)["id"]

        cursor.execute(
            """
            INSERT INTO dompet.budget_members (budget_id, user_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
            """,
            (str(budget_id), str(member_user_id)),
        )
        cursor.execute(
            MEMBER_SELECT + " WHERE bm.budget_id = %s AND bm.user_id = %s",
            (str(budget_id), str(member_user_id)),
        )
        return cursor.fetchone()

    return run_atomic(work, user_id=user_id)


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
            raise NotFoundException(ValueError("Membership not found"))

    return run_atomic(work, user_id=user_id)
