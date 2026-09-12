from ..lib.exceptions import InvalidDataException
from ..utils.db import run_atomic


def _require_owned_account(cursor, user_id, account_id) -> None:
    cursor.execute(
        "SELECT 1 FROM dompet.accounts WHERE id = %s AND user_id = %s",
        (str(account_id), str(user_id)),
    )
    if not cursor.fetchone():
        raise InvalidDataException(ValueError(f"Account not found or not owned by user: {account_id}"))


def list_account_locations(user_id, account_id) -> list[dict]:
    def work(cursor):
        _require_owned_account(cursor, user_id, account_id)
        cursor.execute(
            """
            SELECT l.* FROM dompet.account_locations al
            JOIN dompet.locations l ON l.id = al.location_id
            WHERE al.account_id = %s
            ORDER BY l.name
            """,
            (str(account_id),),
        )
        return cursor.fetchall()

    return run_atomic(work)


def link_location(user_id, account_id, location_id) -> dict:
    def work(cursor):
        _require_owned_account(cursor, user_id, account_id)

        cursor.execute(
            "SELECT 1 FROM dompet.locations WHERE id = %s AND is_active = TRUE",
            (str(location_id),),
        )
        if not cursor.fetchone():
            raise InvalidDataException(ValueError(f"Location not found or inactive: {location_id}"))

        cursor.execute(
            """
            INSERT INTO dompet.account_locations (account_id, location_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
            """,
            (str(account_id), str(location_id)),
        )
        cursor.execute(
            """
            SELECT account_id, location_id, created_at FROM dompet.account_locations
            WHERE account_id = %s AND location_id = %s
            """,
            (str(account_id), str(location_id)),
        )
        return cursor.fetchone()

    return run_atomic(work)


def unlink_location(user_id, account_id, location_id) -> None:
    def work(cursor):
        _require_owned_account(cursor, user_id, account_id)
        cursor.execute(
            "DELETE FROM dompet.account_locations WHERE account_id = %s AND location_id = %s RETURNING account_id",
            (str(account_id), str(location_id)),
        )
        if not cursor.fetchone():
            raise InvalidDataException(ValueError("Link not found"))

    return run_atomic(work)
