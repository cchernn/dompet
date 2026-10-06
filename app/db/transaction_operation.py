import uuid
from datetime import date, datetime
from decimal import Decimal

from ..lib.exceptions import InvalidDataException, NotFoundException
from ..utils.db import run_atomic
from .operations import row_to_dict, record_operation

OPERATION_TYPES = ("CREATE", "UPDATE", "DEACTIVATE", "REACTIVATE", "ROLLBACK")
TRANSACTION_TYPES = ("expenditure", "income", "transfer")

CREATE_REQUIRED_FIELDS = (
    "name", "type", "amount", "currency_code",
    "source_account_id", "destination_account_id",
)
UPDATABLE_FIELDS = (
    "datetime", "name", "type", "amount", "currency_code",
    "category_id", "source_account_id", "destination_account_id",
    "source_location_id", "destination_location_id",
)


def _has_timezone_offset(value) -> bool:
    if isinstance(value, datetime):
        return value.tzinfo is not None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _resolve_datetime(body: dict, current: dict = None) -> str:
    """`date` is accepted as a convenience input (defaults to midnight, or on
    an edit preserves the existing time-of-day) but only `datetime` is
    persisted -- there's no separate stored date column.

    `datetime` must carry an explicit timezone offset (e.g. a trailing `Z`
    or `+08:00`) -- a naive value would be silently interpreted as UTC by
    Postgres, which is exactly the bug that corrupted ~2000 Firefly-sourced
    rows and 8 real user-created transactions (both since corrected). A
    well-behaved client already produces this for free (e.g. JS's
    `Date.toISOString()` always ends in `Z`); this just refuses to
    silently accept the ambiguous case instead of guessing."""
    if body.get("datetime"):
        if not _has_timezone_offset(body["datetime"]):
            raise InvalidDataException(ValueError(
                "datetime must include an explicit timezone offset (e.g. a trailing 'Z' or '+08:00') "
                "-- a value without one would be silently interpreted as UTC"
            ))
        return body["datetime"]
    if body.get("date"):
        new_date = date.fromisoformat(body["date"])
        if current is not None:
            return current["datetime"].replace(year=new_date.year, month=new_date.month, day=new_date.day)
        return f"{body['date']} 00:00:00"
    if current is not None:
        return current["datetime"]
    raise InvalidDataException(ValueError("Either 'date' or 'datetime' is required"))


def _require_currency(cursor, currency_code: str) -> None:
    cursor.execute(
        "SELECT 1 FROM dompet.currencies WHERE code = %s AND is_active = TRUE",
        (currency_code,),
    )
    if not cursor.fetchone():
        raise InvalidDataException(ValueError(f"Unknown or inactive currency: {currency_code}"))


def _require_owned_account(cursor, user_id, account_id, field_name: str) -> None:
    cursor.execute(
        "SELECT 1 FROM dompet.accounts WHERE id = %s AND user_id = %s AND is_active = TRUE",
        (account_id, str(user_id)),
    )
    if not cursor.fetchone():
        raise InvalidDataException(
            ValueError(f"Unknown, inactive, or not-owned account for {field_name}: {account_id}")
        )


def _require_accessible_category(cursor, user_id, category_id) -> None:
    if category_id is None:
        return
    cursor.execute(
        "SELECT 1 FROM dompet.categories WHERE id = %s AND (user_id = %s OR user_id IS NULL) AND is_active = TRUE",
        (category_id, str(user_id)),
    )
    if not cursor.fetchone():
        raise InvalidDataException(ValueError(f"Unknown, inactive, or inaccessible category: {category_id}"))


def _require_accessible_location(cursor, location_id, account_id, field_name: str) -> None:
    """Locations have no owner concept (global, like currencies) -- instead
    each leg's location must already be linked, via account_locations, to
    that same leg's account. Source and destination are validated
    independently since a transaction can genuinely have two different
    real-world locations (e.g. cash withdrawn at one place into a wallet
    destined for spending at another)."""
    if location_id is None:
        return
    cursor.execute(
        """
        SELECT 1 FROM dompet.locations loc
        JOIN dompet.account_locations al ON al.location_id = loc.id
        WHERE loc.id = %s AND loc.is_active = TRUE AND al.account_id = %s
        """,
        (location_id, account_id),
    )
    if not cursor.fetchone():
        raise InvalidDataException(
            ValueError(f"Unknown, inactive, or not linked to {field_name}: {location_id}")
        )


def _validate_fields(cursor, user_id, fields: dict) -> None:
    if fields.get("type") not in TRANSACTION_TYPES:
        raise InvalidDataException(ValueError(f"Invalid transaction type: {fields.get('type')}"))
    if Decimal(str(fields["amount"])) < 0:
        raise InvalidDataException(ValueError("Amount must be non-negative"))
    _require_currency(cursor, fields["currency_code"])
    _require_owned_account(cursor, user_id, fields["source_account_id"], "source_account_id")
    _require_owned_account(cursor, user_id, fields["destination_account_id"], "destination_account_id")
    _require_accessible_category(cursor, user_id, fields.get("category_id"))
    _require_accessible_location(
        cursor, fields.get("source_location_id"), fields["source_account_id"], "source_account_id"
    )
    _require_accessible_location(
        cursor, fields.get("destination_location_id"), fields["destination_account_id"], "destination_account_id"
    )


def _lock_owned_transaction(cursor, user_id, transaction_id) -> dict:
    cursor.execute(
        "SELECT * FROM dompet.transactions WHERE id = %s AND user_id = %s FOR UPDATE",
        (str(transaction_id), str(user_id)),
    )
    row = cursor.fetchone()
    if not row:
        raise NotFoundException(
            ValueError(f"Transaction not found or not owned by user: {transaction_id}")
        )
    return row


def create_transaction(user_id, body: dict, metadata: dict = None) -> dict:
    missing = [f for f in CREATE_REQUIRED_FIELDS if body.get(f) in (None, "")]
    if missing:
        raise InvalidDataException(ValueError(f"Missing required fields: {', '.join(missing)}"))

    fields = {field: body[field] for field in CREATE_REQUIRED_FIELDS}
    fields["category_id"] = body.get("category_id")
    fields["source_location_id"] = body.get("source_location_id")
    fields["destination_location_id"] = body.get("destination_location_id")
    fields["datetime"] = _resolve_datetime(body)

    def work(cursor):
        _validate_fields(cursor, user_id, fields)

        transaction_id = uuid.uuid4()
        cursor.execute(
            """
            INSERT INTO dompet.transactions
                (id, user_id, datetime, name, type, amount, currency_code,
                 category_id, source_account_id, destination_account_id,
                 source_location_id, destination_location_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (
                str(transaction_id), str(user_id), fields["datetime"], fields["name"],
                fields["type"], fields["amount"], fields["currency_code"],
                fields["category_id"], fields["source_account_id"], fields["destination_account_id"],
                fields["source_location_id"], fields["destination_location_id"],
            ),
        )
        after_row = row_to_dict(cursor.fetchone())

        record_operation(cursor, "transaction", transaction_id, user_id, "CREATE", None, after_row, metadata)
        return after_row

    return run_atomic(work, user_id=user_id)


def update_transaction(user_id, transaction_id, body: dict, metadata: dict = None) -> dict:
    patch = {k: v for k, v in body.items() if k in UPDATABLE_FIELDS}
    if not patch and "date" not in body:
        raise InvalidDataException(ValueError("No updatable fields provided"))

    def work(cursor):
        current = _lock_owned_transaction(cursor, user_id, transaction_id)
        before_row = row_to_dict(current)

        merged = {field: patch.get(field, current[field]) for field in UPDATABLE_FIELDS}
        merged["datetime"] = _resolve_datetime(body, current)
        _validate_fields(cursor, user_id, merged)

        cursor.execute(
            """
            UPDATE dompet.transactions
            SET datetime = %s, name = %s, type = %s, amount = %s, currency_code = %s,
                category_id = %s, source_account_id = %s, destination_account_id = %s,
                source_location_id = %s, destination_location_id = %s, updated_at = NOW()
            WHERE id = %s AND user_id = %s
            RETURNING *
            """,
            (
                merged["datetime"], merged["name"], merged["type"], merged["amount"],
                merged["currency_code"], merged["category_id"],
                merged["source_account_id"], merged["destination_account_id"],
                merged["source_location_id"], merged["destination_location_id"],
                str(transaction_id), str(user_id),
            ),
        )
        after_row = row_to_dict(cursor.fetchone())

        record_operation(cursor, "transaction", transaction_id, user_id, "UPDATE", before_row, after_row, metadata)
        return after_row

    return run_atomic(work, user_id=user_id)


def _set_active_state(user_id, transaction_id, active: bool, operation_type: str, metadata: dict = None) -> dict:
    def work(cursor):
        current = _lock_owned_transaction(cursor, user_id, transaction_id)
        before_row = row_to_dict(current)

        if current["is_active"] == active:
            state = "active" if active else "inactive"
            raise InvalidDataException(ValueError(f"Transaction is already {state}"))

        cursor.execute(
            """
            UPDATE dompet.transactions
            SET is_active = %s, updated_at = NOW()
            WHERE id = %s AND user_id = %s
            RETURNING *
            """,
            (active, str(transaction_id), str(user_id)),
        )
        after_row = row_to_dict(cursor.fetchone())

        record_operation(cursor, "transaction", transaction_id, user_id, operation_type, before_row, after_row, metadata)
        return after_row

    return run_atomic(work, user_id=user_id)


def deactivate_transaction(user_id, transaction_id, metadata: dict = None) -> dict:
    return _set_active_state(user_id, transaction_id, False, "DEACTIVATE", metadata)


def reactivate_transaction(user_id, transaction_id, metadata: dict = None) -> dict:
    return _set_active_state(user_id, transaction_id, True, "REACTIVATE", metadata)


def rollback_transaction(user_id, transaction_id, target_operation_id, metadata: dict = None) -> dict:
    def work(cursor):
        current = _lock_owned_transaction(cursor, user_id, transaction_id)
        before_row = row_to_dict(current)

        cursor.execute(
            """
            SELECT after_data FROM dompet.operations
            WHERE id = %s AND entity_type = 'transaction' AND entity_id = %s AND user_id = %s
            """,
            (str(target_operation_id), str(transaction_id), str(user_id)),
        )
        target = cursor.fetchone()
        if not target or target["after_data"] is None:
            raise InvalidDataException(
                ValueError(f"No restorable state found for operation: {target_operation_id}")
            )
        restore = target["after_data"]

        # Snapshots recorded before the `datetime` column existed have no such
        # key at all -- fall back to midnight of that snapshot's date rather
        # than KeyError on an old rollback target.
        restore_datetime = restore.get("datetime") or f"{restore['date']} 00:00:00"
        # Snapshots recorded before source/destination_location_id existed
        # (or before the single location_id it briefly replaced) have
        # neither key -- default both to unset rather than KeyError.
        restore_source_location_id = restore.get("source_location_id")
        restore_destination_location_id = restore.get("destination_location_id")

        cursor.execute(
            """
            UPDATE dompet.transactions
            SET datetime = %s, name = %s, type = %s, amount = %s, currency_code = %s,
                category_id = %s, source_account_id = %s, destination_account_id = %s,
                source_location_id = %s, destination_location_id = %s, is_active = %s, updated_at = NOW()
            WHERE id = %s AND user_id = %s
            RETURNING *
            """,
            (
                restore_datetime, restore["name"], restore["type"], restore["amount"],
                restore["currency_code"], restore["category_id"],
                restore["source_account_id"], restore["destination_account_id"],
                restore_source_location_id, restore_destination_location_id,
                restore["is_active"], str(transaction_id), str(user_id),
            ),
        )
        after_row = row_to_dict(cursor.fetchone())

        rollback_metadata = {**(metadata or {}), "rollback_target_operation_id": str(target_operation_id)}
        record_operation(cursor, "transaction", transaction_id, user_id, "ROLLBACK", before_row, after_row, rollback_metadata)
        return after_row

    return run_atomic(work, user_id=user_id)
