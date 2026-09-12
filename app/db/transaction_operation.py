import uuid
from datetime import date, datetime
from decimal import Decimal

from psycopg2.extras import Json

from ..lib.exceptions import InvalidDataException
from ..utils.db import run_atomic

OPERATION_TYPES = ("CREATE", "UPDATE", "DEACTIVATE", "REACTIVATE", "ROLLBACK")
TRANSACTION_TYPES = ("expenditure", "income", "transfer")

CREATE_REQUIRED_FIELDS = (
    "date", "name", "type", "amount", "currency_code",
    "source_account_id", "destination_account_id",
)
UPDATABLE_FIELDS = (
    "date", "name", "type", "amount", "currency_code",
    "category_id", "source_account_id", "destination_account_id",
)


def _jsonable(value):
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def _row_to_dict(row) -> dict:
    return {k: _jsonable(v) for k, v in dict(row).items()}


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


def _validate_fields(cursor, user_id, fields: dict) -> None:
    if fields.get("type") not in TRANSACTION_TYPES:
        raise InvalidDataException(ValueError(f"Invalid transaction type: {fields.get('type')}"))
    if Decimal(str(fields["amount"])) < 0:
        raise InvalidDataException(ValueError("Amount must be non-negative"))
    _require_currency(cursor, fields["currency_code"])
    _require_owned_account(cursor, user_id, fields["source_account_id"], "source_account_id")
    _require_owned_account(cursor, user_id, fields["destination_account_id"], "destination_account_id")
    _require_accessible_category(cursor, user_id, fields.get("category_id"))


def _lock_owned_transaction(cursor, user_id, transaction_id) -> dict:
    cursor.execute(
        "SELECT * FROM dompet.transactions WHERE id = %s AND user_id = %s FOR UPDATE",
        (str(transaction_id), str(user_id)),
    )
    row = cursor.fetchone()
    if not row:
        raise InvalidDataException(
            ValueError(f"Transaction not found or not owned by user: {transaction_id}")
        )
    return row


def _record_operation(cursor, transaction_id, user_id, operation_type, before_data, after_data, metadata=None):
    cursor.execute(
        """
        INSERT INTO dompet.transaction_operations
            (transaction_id, user_id, operation_type, before_data, after_data, metadata)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            str(transaction_id),
            str(user_id),
            operation_type,
            Json(before_data) if before_data is not None else None,
            Json(after_data) if after_data is not None else None,
            Json(metadata) if metadata is not None else None,
        ),
    )
    return cursor.fetchone()["id"]


def create_transaction(user_id, body: dict, metadata: dict = None) -> dict:
    missing = [f for f in CREATE_REQUIRED_FIELDS if body.get(f) in (None, "")]
    if missing:
        raise InvalidDataException(ValueError(f"Missing required fields: {', '.join(missing)}"))

    fields = {field: body[field] for field in CREATE_REQUIRED_FIELDS}
    fields["category_id"] = body.get("category_id")

    def work(cursor):
        _validate_fields(cursor, user_id, fields)

        transaction_id = uuid.uuid4()
        cursor.execute(
            """
            INSERT INTO dompet.transactions
                (id, user_id, date, name, type, amount, currency_code,
                 category_id, source_account_id, destination_account_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (
                str(transaction_id), str(user_id), fields["date"], fields["name"],
                fields["type"], fields["amount"], fields["currency_code"],
                fields["category_id"], fields["source_account_id"], fields["destination_account_id"],
            ),
        )
        after_row = _row_to_dict(cursor.fetchone())

        _record_operation(cursor, transaction_id, user_id, "CREATE", None, after_row, metadata)
        return after_row

    return run_atomic(work)


def update_transaction(user_id, transaction_id, body: dict, metadata: dict = None) -> dict:
    patch = {k: v for k, v in body.items() if k in UPDATABLE_FIELDS}
    if not patch:
        raise InvalidDataException(ValueError("No updatable fields provided"))

    def work(cursor):
        current = _lock_owned_transaction(cursor, user_id, transaction_id)
        before_row = _row_to_dict(current)

        merged = {field: patch.get(field, current[field]) for field in UPDATABLE_FIELDS}
        _validate_fields(cursor, user_id, merged)

        cursor.execute(
            """
            UPDATE dompet.transactions
            SET date = %s, name = %s, type = %s, amount = %s, currency_code = %s,
                category_id = %s, source_account_id = %s, destination_account_id = %s,
                updated_at = NOW()
            WHERE id = %s AND user_id = %s
            RETURNING *
            """,
            (
                merged["date"], merged["name"], merged["type"], merged["amount"],
                merged["currency_code"], merged["category_id"],
                merged["source_account_id"], merged["destination_account_id"],
                str(transaction_id), str(user_id),
            ),
        )
        after_row = _row_to_dict(cursor.fetchone())

        _record_operation(cursor, transaction_id, user_id, "UPDATE", before_row, after_row, metadata)
        return after_row

    return run_atomic(work)


def _set_active_state(user_id, transaction_id, active: bool, operation_type: str, metadata: dict = None) -> dict:
    def work(cursor):
        current = _lock_owned_transaction(cursor, user_id, transaction_id)
        before_row = _row_to_dict(current)

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
        after_row = _row_to_dict(cursor.fetchone())

        _record_operation(cursor, transaction_id, user_id, operation_type, before_row, after_row, metadata)
        return after_row

    return run_atomic(work)


def deactivate_transaction(user_id, transaction_id, metadata: dict = None) -> dict:
    return _set_active_state(user_id, transaction_id, False, "DEACTIVATE", metadata)


def reactivate_transaction(user_id, transaction_id, metadata: dict = None) -> dict:
    return _set_active_state(user_id, transaction_id, True, "REACTIVATE", metadata)


def rollback_transaction(user_id, transaction_id, target_operation_id, metadata: dict = None) -> dict:
    def work(cursor):
        current = _lock_owned_transaction(cursor, user_id, transaction_id)
        before_row = _row_to_dict(current)

        cursor.execute(
            """
            SELECT after_data FROM dompet.transaction_operations
            WHERE id = %s AND transaction_id = %s AND user_id = %s
            """,
            (str(target_operation_id), str(transaction_id), str(user_id)),
        )
        target = cursor.fetchone()
        if not target or target["after_data"] is None:
            raise InvalidDataException(
                ValueError(f"No restorable state found for operation: {target_operation_id}")
            )
        restore = target["after_data"]

        cursor.execute(
            """
            UPDATE dompet.transactions
            SET date = %s, name = %s, type = %s, amount = %s, currency_code = %s,
                category_id = %s, source_account_id = %s, destination_account_id = %s,
                is_active = %s, updated_at = NOW()
            WHERE id = %s AND user_id = %s
            RETURNING *
            """,
            (
                restore["date"], restore["name"], restore["type"], restore["amount"],
                restore["currency_code"], restore["category_id"],
                restore["source_account_id"], restore["destination_account_id"],
                restore["is_active"], str(transaction_id), str(user_id),
            ),
        )
        after_row = _row_to_dict(cursor.fetchone())

        rollback_metadata = {**(metadata or {}), "rollback_target_operation_id": str(target_operation_id)}
        _record_operation(cursor, transaction_id, user_id, "ROLLBACK", before_row, after_row, rollback_metadata)
        return after_row

    return run_atomic(work)
