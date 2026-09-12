from ..lib.exceptions import InvalidDataException
from ..utils.db import run_atomic


def list_tags(user_id, include_inactive: bool = False) -> list[dict]:
    def work(cursor):
        query = "SELECT * FROM dompet.tags WHERE user_id = %s"
        params = [str(user_id)]
        if not include_inactive:
            query += " AND is_active = TRUE"
        query += " ORDER BY name"
        cursor.execute(query, params)
        return cursor.fetchall()

    return run_atomic(work)


def create_tag(user_id, body: dict) -> dict:
    name = body.get("name")
    if not name:
        raise InvalidDataException(ValueError("name is required"))

    def work(cursor):
        cursor.execute(
            "SELECT * FROM dompet.tags WHERE user_id = %s AND name = %s",
            (str(user_id), name),
        )
        existing = cursor.fetchone()
        if existing:
            return existing

        cursor.execute(
            "INSERT INTO dompet.tags (user_id, name) VALUES (%s, %s) RETURNING *",
            (str(user_id), name),
        )
        return cursor.fetchone()

    return run_atomic(work)
