import re
import uuid

from ..lib.exceptions import InvalidDataException
from ..utils.db import run_atomic, paginate
from .operations import row_to_dict, record_operation

UPDATABLE_FIELDS = ("name", "description")


def _generate_code(name: str) -> str:
    """code is no longer something a user needs to pick -- accounts are
    created by name, duplicates and all, since `id` is what actually
    distinguishes rows. Auto-generates a short, effectively-unique code so
    the underlying UNIQUE(user_id, code) constraint (and the migration
    scripts' existing slugify_code-based dedup trick) keep working
    unchanged for anyone still passing one explicitly."""
    slug = re.sub(r"[^A-Za-z0-9]+", "", name).upper()[:20] or "ACCT"
    return f"{slug}-{uuid.uuid4().hex[:8]}"


def list_accounts(user_id, page: int, page_size: int, include_inactive: bool = False) -> tuple[list[dict], dict]:
    def work(cursor):
        query = "SELECT * FROM dompet.accounts WHERE user_id = %s"
        params = [str(user_id)]
        if not include_inactive:
            query += " AND is_active = TRUE"
        query += " ORDER BY name"
        return paginate(cursor, query, params, page, page_size)

    return run_atomic(work, user_id=user_id)


def get_account(user_id, account_id) -> dict:
    def work(cursor):
        cursor.execute(
            "SELECT * FROM dompet.accounts WHERE id = %s AND user_id = %s",
            (str(account_id), str(user_id)),
        )
        row = cursor.fetchone()
        if not row:
            raise InvalidDataException(ValueError(f"Account not found: {account_id}"))
        return row

    return run_atomic(work, user_id=user_id)


def create_account(user_id, body: dict) -> dict:
    name = body.get("name")
    if not name:
        raise InvalidDataException(ValueError("name is required"))
    code = body.get("code") or _generate_code(name)

    def work(cursor):
        cursor.execute(
            """
            INSERT INTO dompet.accounts (user_id, code, name, description)
            VALUES (%s, %s, %s, %s)
            RETURNING *
            """,
            (str(user_id), code, name, body.get("description")),
        )
        row = cursor.fetchone()
        record_operation(cursor, "account", row["id"], user_id, "CREATE", None, row_to_dict(row))
        return row

    return run_atomic(work, user_id=user_id)


def update_account(user_id, account_id, body: dict) -> dict:
    patch = {k: v for k, v in body.items() if k in UPDATABLE_FIELDS}
    if not patch:
        raise InvalidDataException(ValueError("No updatable fields provided"))

    def work(cursor):
        cursor.execute(
            "SELECT * FROM dompet.accounts WHERE id = %s AND user_id = %s FOR UPDATE",
            (str(account_id), str(user_id)),
        )
        before = cursor.fetchone()
        if not before:
            raise InvalidDataException(ValueError(f"Account not found: {account_id}"))

        set_clause = ", ".join(f"{field} = %s" for field in patch)
        cursor.execute(
            f"""
            UPDATE dompet.accounts SET {set_clause}, updated_at = NOW()
            WHERE id = %s AND user_id = %s
            RETURNING *
            """,
            (*patch.values(), str(account_id), str(user_id)),
        )
        after = cursor.fetchone()
        record_operation(cursor, "account", account_id, user_id, "UPDATE", row_to_dict(before), row_to_dict(after))
        return after

    return run_atomic(work, user_id=user_id)


def _set_active_state(user_id, account_id, active: bool, operation_type: str) -> dict:
    def work(cursor):
        cursor.execute(
            "SELECT * FROM dompet.accounts WHERE id = %s AND user_id = %s FOR UPDATE",
            (str(account_id), str(user_id)),
        )
        before = cursor.fetchone()
        if not before:
            raise InvalidDataException(ValueError(f"Account not found: {account_id}"))

        cursor.execute(
            """
            UPDATE dompet.accounts SET is_active = %s, updated_at = NOW()
            WHERE id = %s AND user_id = %s
            RETURNING *
            """,
            (active, str(account_id), str(user_id)),
        )
        after = cursor.fetchone()
        record_operation(cursor, "account", account_id, user_id, operation_type, row_to_dict(before), row_to_dict(after))
        return after

    return run_atomic(work, user_id=user_id)


def deactivate_account(user_id, account_id) -> dict:
    return _set_active_state(user_id, account_id, False, "DEACTIVATE")


def reactivate_account(user_id, account_id) -> dict:
    return _set_active_state(user_id, account_id, True, "REACTIVATE")
