from ..lib.exceptions import InvalidDataException
from ..utils.db import run_atomic, paginate

UPDATABLE_FIELDS = ("name",)


def list_tags(user_id, page: int, page_size: int, include_inactive: bool = False) -> tuple[list[dict], dict]:
    def work(cursor):
        query = "SELECT * FROM dompet.tags WHERE user_id = %s"
        params = [str(user_id)]
        if not include_inactive:
            query += " AND is_active = TRUE"
        query += " ORDER BY name"
        return paginate(cursor, query, params, page, page_size)

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


def update_tag(user_id, tag_id, body: dict) -> dict:
    patch = {k: v for k, v in body.items() if k in UPDATABLE_FIELDS}
    if not patch:
        raise InvalidDataException(ValueError("No updatable fields provided"))

    def work(cursor):
        cursor.execute(
            "SELECT 1 FROM dompet.tags WHERE id = %s AND user_id = %s FOR UPDATE",
            (str(tag_id), str(user_id)),
        )
        if not cursor.fetchone():
            raise InvalidDataException(ValueError(f"Tag not found or not owned by user: {tag_id}"))

        set_clause = ", ".join(f"{field} = %s" for field in patch)
        cursor.execute(
            f"UPDATE dompet.tags SET {set_clause}, updated_at = NOW() WHERE id = %s AND user_id = %s RETURNING *",
            (*patch.values(), str(tag_id), str(user_id)),
        )
        return cursor.fetchone()

    return run_atomic(work)


def delete_tag(user_id, tag_id) -> dict:
    def work(cursor):
        cursor.execute(
            "UPDATE dompet.tags SET is_active = FALSE, updated_at = NOW() WHERE id = %s AND user_id = %s RETURNING *",
            (str(tag_id), str(user_id)),
        )
        row = cursor.fetchone()
        if not row:
            raise InvalidDataException(ValueError(f"Tag not found or not owned by user: {tag_id}"))
        return row

    return run_atomic(work)
