from ..lib.exceptions import InvalidDataException
from ..utils.db import run_atomic

UPDATABLE_FIELDS = ("code", "name", "description")


def list_accounts(user_id, include_inactive: bool = False) -> list[dict]:
    def work(cursor):
        query = "SELECT * FROM dompet.accounts WHERE user_id = %s"
        params = [str(user_id)]
        if not include_inactive:
            query += " AND is_active = TRUE"
        query += " ORDER BY code"
        cursor.execute(query, params)
        return cursor.fetchall()

    return run_atomic(work)


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

    return run_atomic(work)


def create_account(user_id, body: dict) -> dict:
    code = body.get("code")
    name = body.get("name")
    if not code or not name:
        raise InvalidDataException(ValueError("code and name are required"))

    def work(cursor):
        cursor.execute(
            """
            INSERT INTO dompet.accounts (user_id, code, name, description)
            VALUES (%s, %s, %s, %s)
            RETURNING *
            """,
            (str(user_id), code, name, body.get("description")),
        )
        return cursor.fetchone()

    return run_atomic(work)


def update_account(user_id, account_id, body: dict) -> dict:
    patch = {k: v for k, v in body.items() if k in UPDATABLE_FIELDS}
    if not patch:
        raise InvalidDataException(ValueError("No updatable fields provided"))

    def work(cursor):
        cursor.execute(
            "SELECT 1 FROM dompet.accounts WHERE id = %s AND user_id = %s FOR UPDATE",
            (str(account_id), str(user_id)),
        )
        if not cursor.fetchone():
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
        return cursor.fetchone()

    return run_atomic(work)


def _set_active_state(user_id, account_id, active: bool) -> dict:
    def work(cursor):
        cursor.execute(
            """
            UPDATE dompet.accounts SET is_active = %s, updated_at = NOW()
            WHERE id = %s AND user_id = %s
            RETURNING *
            """,
            (active, str(account_id), str(user_id)),
        )
        row = cursor.fetchone()
        if not row:
            raise InvalidDataException(ValueError(f"Account not found: {account_id}"))
        return row

    return run_atomic(work)


def deactivate_account(user_id, account_id) -> dict:
    return _set_active_state(user_id, account_id, False)


def reactivate_account(user_id, account_id) -> dict:
    return _set_active_state(user_id, account_id, True)
