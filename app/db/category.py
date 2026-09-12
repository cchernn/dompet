from ..lib.exceptions import InvalidDataException
from ..utils.db import run_atomic


def list_categories(user_id, include_inactive: bool = False) -> list[dict]:
    def work(cursor):
        query = "SELECT * FROM dompet.categories WHERE (user_id = %s OR user_id IS NULL)"
        params = [str(user_id)]
        if not include_inactive:
            query += " AND is_active = TRUE"
        query += " ORDER BY parent_id NULLS FIRST, name"
        cursor.execute(query, params)
        return cursor.fetchall()

    return run_atomic(work)


def create_category(user_id, body: dict) -> dict:
    name = body.get("name")
    if not name:
        raise InvalidDataException(ValueError("name is required"))
    parent_id = body.get("parent_id")

    def work(cursor):
        if parent_id:
            cursor.execute(
                "SELECT 1 FROM dompet.categories WHERE id = %s AND (user_id = %s OR user_id IS NULL) AND is_active = TRUE",
                (parent_id, str(user_id)),
            )
            if not cursor.fetchone():
                raise InvalidDataException(ValueError(f"Unknown or inaccessible parent category: {parent_id}"))

        cursor.execute(
            """
            SELECT * FROM dompet.categories
            WHERE user_id = %s AND name = %s AND parent_id IS NOT DISTINCT FROM %s
            """,
            (str(user_id), name, parent_id),
        )
        existing = cursor.fetchone()
        if existing:
            return existing

        cursor.execute(
            "INSERT INTO dompet.categories (user_id, name, parent_id) VALUES (%s, %s, %s) RETURNING *",
            (str(user_id), name, parent_id),
        )
        return cursor.fetchone()

    return run_atomic(work)
