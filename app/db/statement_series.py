from datetime import date

from ..lib.exceptions import InvalidDataException, NotFoundException
from ..utils.db import run_atomic, paginate
from .operations import row_to_dict, record_operation
from .statement import sync_statements, _require_currency, _require_owned_account

RECURRENCE_UNITS = ("day", "week", "month", "year")
CREATE_REQUIRED_FIELDS = ("account_id", "recurrence_unit", "recurrence_count", "anchor_date")
UPDATABLE_FIELDS = ("currency_code", "recurrence_unit", "recurrence_count")


def _validate_fields(cursor, fields: dict) -> None:
    if fields["recurrence_unit"] not in RECURRENCE_UNITS:
        raise InvalidDataException(ValueError(f"Invalid recurrence_unit: {fields['recurrence_unit']}"))
    if int(fields["recurrence_count"]) <= 0:
        raise InvalidDataException(ValueError("recurrence_count must be positive"))
    _require_currency(cursor, fields.get("currency_code"))


def list_series(user_id, page: int, page_size: int, include_inactive: bool = False) -> tuple[list[dict], dict]:
    def work(cursor):
        query = "SELECT * FROM dompet.statement_series WHERE user_id = %s"
        params = [str(user_id)]
        if not include_inactive:
            query += " AND is_active = TRUE"
        query += " ORDER BY created_at"
        return paginate(cursor, query, params, page, page_size)

    return run_atomic(work, user_id=user_id)


def get_series(user_id, series_id) -> dict:
    def work(cursor):
        cursor.execute(
            "SELECT * FROM dompet.statement_series WHERE id = %s AND user_id = %s",
            (str(series_id), str(user_id)),
        )
        row = cursor.fetchone()
        if not row:
            raise NotFoundException(ValueError(f"Statement series not found: {series_id}"))
        return row

    return run_atomic(work, user_id=user_id)


def create_series(user_id, body: dict) -> dict:
    missing = [f for f in CREATE_REQUIRED_FIELDS if body.get(f) in (None, "")]
    if missing:
        raise InvalidDataException(ValueError(f"Missing required fields: {', '.join(missing)}"))

    fields = {field: body[field] for field in CREATE_REQUIRED_FIELDS}
    fields["currency_code"] = body.get("currency_code")
    try:
        date.fromisoformat(str(fields["anchor_date"]))
    except ValueError:
        raise InvalidDataException(ValueError(f"anchor_date must be an ISO date (YYYY-MM-DD): {fields['anchor_date']}"))

    def work(cursor):
        _validate_fields(cursor, fields)
        _require_owned_account(cursor, user_id, fields["account_id"])
        # A second active series on the same account is rejected by
        # statement_series_account_active_unique (surfaces as a 409).
        cursor.execute(
            """
            INSERT INTO dompet.statement_series
                (user_id, account_id, currency_code, recurrence_unit, recurrence_count, anchor_date)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (
                str(user_id), fields["account_id"], fields["currency_code"],
                fields["recurrence_unit"], fields["recurrence_count"], fields["anchor_date"],
            ),
        )
        row = cursor.fetchone()
        record_operation(cursor, "statement_series", row["id"], user_id, "CREATE", None, row_to_dict(row))

        # Materialize the first occurrence immediately, so it shows up in
        # GET /statements right away instead of waiting for the next
        # on-demand sync.
        sync_statements(cursor, user_id)
        return row

    return run_atomic(work, user_id=user_id)


def update_series(user_id, series_id, body: dict) -> dict:
    """Only affects occurrences generated after the edit -- existing ones are
    never rewritten. The account and anchor_date are fixed at creation."""
    patch = {k: v for k, v in body.items() if k in UPDATABLE_FIELDS}
    if not patch:
        raise InvalidDataException(ValueError("No updatable fields provided"))

    def work(cursor):
        cursor.execute(
            "SELECT * FROM dompet.statement_series WHERE id = %s AND user_id = %s FOR UPDATE",
            (str(series_id), str(user_id)),
        )
        before = cursor.fetchone()
        if not before:
            raise NotFoundException(ValueError(f"Statement series not found: {series_id}"))

        merged = {field: patch.get(field, before[field]) for field in UPDATABLE_FIELDS}
        _validate_fields(cursor, merged)

        cursor.execute(
            """
            UPDATE dompet.statement_series
            SET currency_code = %s, recurrence_unit = %s, recurrence_count = %s, updated_at = NOW()
            WHERE id = %s AND user_id = %s
            RETURNING *
            """,
            (
                merged["currency_code"], merged["recurrence_unit"], merged["recurrence_count"],
                str(series_id), str(user_id),
            ),
        )
        after = cursor.fetchone()
        record_operation(cursor, "statement_series", series_id, user_id, "UPDATE", row_to_dict(before), row_to_dict(after))
        return after

    return run_atomic(work, user_id=user_id)


def deactivate_series(user_id, series_id) -> dict:
    """Stops future occurrences from being generated, and frees the account
    for a new series; existing statements (received or not) are untouched."""
    def work(cursor):
        cursor.execute(
            "SELECT * FROM dompet.statement_series WHERE id = %s AND user_id = %s FOR UPDATE",
            (str(series_id), str(user_id)),
        )
        before = cursor.fetchone()
        if not before:
            raise NotFoundException(ValueError(f"Statement series not found: {series_id}"))

        cursor.execute(
            "UPDATE dompet.statement_series SET is_active = FALSE, updated_at = NOW() WHERE id = %s AND user_id = %s RETURNING *",
            (str(series_id), str(user_id)),
        )
        after = cursor.fetchone()
        record_operation(cursor, "statement_series", series_id, user_id, "DEACTIVATE", row_to_dict(before), row_to_dict(after))
        return after

    return run_atomic(work, user_id=user_id)
