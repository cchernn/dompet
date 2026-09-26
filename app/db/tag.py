from ..lib.exceptions import InvalidDataException
from ..utils.db import run_atomic, paginate
from .operations import row_to_dict, record_operation

UPDATABLE_FIELDS = ("name",)


def list_tags(user_id, page: int, page_size: int, include_inactive: bool = False) -> tuple[list[dict], dict]:
    def work(cursor):
        query = "SELECT * FROM dompet.tags WHERE user_id = %s"
        params = [str(user_id)]
        if not include_inactive:
            query += " AND is_active = TRUE"
        query += " ORDER BY name"
        return paginate(cursor, query, params, page, page_size)

    return run_atomic(work, user_id=user_id)


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
        row = cursor.fetchone()
        record_operation(cursor, "tag", row["id"], user_id, "CREATE", None, row_to_dict(row))
        return row

    return run_atomic(work, user_id=user_id)


def update_tag(user_id, tag_id, body: dict) -> dict:
    patch = {k: v for k, v in body.items() if k in UPDATABLE_FIELDS}
    if not patch:
        raise InvalidDataException(ValueError("No updatable fields provided"))

    def work(cursor):
        cursor.execute(
            "SELECT * FROM dompet.tags WHERE id = %s AND user_id = %s FOR UPDATE",
            (str(tag_id), str(user_id)),
        )
        before = cursor.fetchone()
        if not before:
            raise InvalidDataException(ValueError(f"Tag not found or not owned by user: {tag_id}"))

        set_clause = ", ".join(f"{field} = %s" for field in patch)
        cursor.execute(
            f"UPDATE dompet.tags SET {set_clause}, updated_at = NOW() WHERE id = %s AND user_id = %s RETURNING *",
            (*patch.values(), str(tag_id), str(user_id)),
        )
        after = cursor.fetchone()
        record_operation(cursor, "tag", tag_id, user_id, "UPDATE", row_to_dict(before), row_to_dict(after))
        return after

    return run_atomic(work, user_id=user_id)


def delete_tag(user_id, tag_id) -> dict:
    def work(cursor):
        cursor.execute(
            "SELECT * FROM dompet.tags WHERE id = %s AND user_id = %s FOR UPDATE",
            (str(tag_id), str(user_id)),
        )
        before = cursor.fetchone()
        if not before:
            raise InvalidDataException(ValueError(f"Tag not found or not owned by user: {tag_id}"))

        cursor.execute(
            "UPDATE dompet.tags SET is_active = FALSE, updated_at = NOW() WHERE id = %s AND user_id = %s RETURNING *",
            (str(tag_id), str(user_id)),
        )
        after = cursor.fetchone()
        record_operation(cursor, "tag", tag_id, user_id, "DEACTIVATE", row_to_dict(before), row_to_dict(after))
        return after

    return run_atomic(work, user_id=user_id)
