from ..lib.exceptions import InvalidDataException
from ..utils.db import run_atomic

UPDATABLE_FIELDS = ("name", "parent_id")


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


def update_category(user_id, category_id, body: dict) -> dict:
    patch = {k: v for k, v in body.items() if k in UPDATABLE_FIELDS}
    if not patch:
        raise InvalidDataException(ValueError("No updatable fields provided"))

    def work(cursor):
        cursor.execute(
            "SELECT 1 FROM dompet.categories WHERE id = %s AND user_id = %s FOR UPDATE",
            (str(category_id), str(user_id)),
        )
        if not cursor.fetchone():
            raise InvalidDataException(ValueError(f"Category not found or not owned by user: {category_id}"))

        parent_id = patch.get("parent_id")
        if parent_id:
            if str(parent_id) == str(category_id):
                raise InvalidDataException(ValueError("A category cannot be its own parent"))
            cursor.execute(
                "SELECT 1 FROM dompet.categories WHERE id = %s AND (user_id = %s OR user_id IS NULL) AND is_active = TRUE",
                (parent_id, str(user_id)),
            )
            if not cursor.fetchone():
                raise InvalidDataException(ValueError(f"Unknown or inaccessible parent category: {parent_id}"))

        set_clause = ", ".join(f"{field} = %s" for field in patch)
        cursor.execute(
            f"""
            UPDATE dompet.categories SET {set_clause}, updated_at = NOW()
            WHERE id = %s AND user_id = %s
            RETURNING *
            """,
            (*patch.values(), str(category_id), str(user_id)),
        )
        return cursor.fetchone()

    return run_atomic(work)


def delete_category(user_id, category_id) -> dict:
    def work(cursor):
        cursor.execute(
            """
            UPDATE dompet.categories SET is_active = FALSE, updated_at = NOW()
            WHERE id = %s AND user_id = %s
            RETURNING *
            """,
            (str(category_id), str(user_id)),
        )
        row = cursor.fetchone()
        if not row:
            raise InvalidDataException(ValueError(f"Category not found or not owned by user: {category_id}"))
        return row

    return run_atomic(work)
