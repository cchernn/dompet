import re

from psycopg2.extras import Json

from ..lib.exceptions import InvalidDataException, NotFoundException
from ..utils.db import run_atomic

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,30}$")


def _validate_username(username) -> str:
    if not isinstance(username, str) or not USERNAME_RE.match(username):
        raise InvalidDataException(ValueError(
            "username must be 3-30 characters, letters/numbers/underscore only"
        ))
    return username


def _validate_configuration(configuration) -> dict:
    if configuration is None:
        return {}
    if not isinstance(configuration, dict):
        raise InvalidDataException(ValueError("configuration must be an object"))
    return configuration


def get_profile(user_id) -> dict:
    def work(cursor):
        cursor.execute("SELECT * FROM dompet.users WHERE id = %s", (str(user_id),))
        row = cursor.fetchone()
        if not row:
            raise NotFoundException(ValueError("User profile not found"))
        return row

    return run_atomic(work, user_id=user_id)


def create_profile(user_id, body: dict) -> dict:
    username = _validate_username(body.get("username"))
    display_name = body.get("display_name")
    configuration = _validate_configuration(body.get("configuration"))

    def work(cursor):
        cursor.execute("SELECT 1 FROM dompet.users WHERE id = %s", (str(user_id),))
        if cursor.fetchone():
            raise InvalidDataException(ValueError("User profile already exists"))

        cursor.execute(
            """
            INSERT INTO dompet.users (id, username, display_name, configuration)
            VALUES (%s, %s, %s, %s)
            RETURNING *
            """,
            (str(user_id), username, display_name, Json(configuration)),
        )
        return cursor.fetchone()

    return run_atomic(work, user_id=user_id)


def update_profile(user_id, body: dict) -> dict:
    patch = {}
    if "username" in body:
        patch["username"] = _validate_username(body.get("username"))
    if "display_name" in body:
        patch["display_name"] = body.get("display_name")
    if "configuration" in body:
        patch["configuration"] = _validate_configuration(body.get("configuration"))
    if not patch:
        raise InvalidDataException(ValueError("No updatable fields provided"))

    def work(cursor):
        cursor.execute("SELECT 1 FROM dompet.users WHERE id = %s", (str(user_id),))
        if not cursor.fetchone():
            raise NotFoundException(ValueError("User profile not found"))

        set_clause = ", ".join(f"{field} = %s" for field in patch)
        values = [
            Json(v) if field == "configuration" else v
            for field, v in patch.items()
        ]
        cursor.execute(
            f"UPDATE dompet.users SET {set_clause}, updated_at = NOW() WHERE id = %s RETURNING *",
            (*values, str(user_id)),
        )
        return cursor.fetchone()

    return run_atomic(work, user_id=user_id)


def find_by_username(cursor, username) -> dict:
    """Looks up a user's public profile by username, for callers (e.g.
    budget invites) that only know the other person's username, not their
    Cognito UUID. Takes an existing cursor so it composes into a caller's
    own transaction (e.g. budget_member.add_member's ownership check)."""
    cursor.execute(
        "SELECT * FROM dompet.vw_users_public WHERE LOWER(username) = LOWER(%s)",
        (username,),
    )
    row = cursor.fetchone()
    if not row:
        raise NotFoundException(ValueError(f"No user found with username: {username}"))
    return row
