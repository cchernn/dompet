from ..lib.exceptions import InvalidDataException, NotFoundException
from ..utils.db import run_atomic, paginate
from .operations import row_to_dict, record_operation
from .bill import sync_bills

RECURRENCE_UNITS = ("day", "week", "month", "year")
CREATE_REQUIRED_FIELDS = ("name", "amount", "currency_code", "recurrence_unit", "recurrence_count", "anchor_date")
UPDATABLE_FIELDS = (
    "name", "amount", "currency_code", "category_id", "account_id",
    "recurrence_unit", "recurrence_count",
)


def _require_currency(cursor, currency_code: str) -> None:
    cursor.execute(
        "SELECT 1 FROM dompet.currencies WHERE code = %s AND is_active = TRUE",
        (currency_code,),
    )
    if not cursor.fetchone():
        raise InvalidDataException(ValueError(f"Unknown or inactive currency: {currency_code}"))


def _require_owned_account(cursor, user_id, account_id) -> None:
    if account_id is None:
        return
    cursor.execute(
        "SELECT 1 FROM dompet.accounts WHERE id = %s AND user_id = %s AND is_active = TRUE",
        (account_id, str(user_id)),
    )
    if not cursor.fetchone():
        raise InvalidDataException(ValueError(f"Unknown, inactive, or not-owned account: {account_id}"))


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
    if float(fields["amount"]) < 0:
        raise InvalidDataException(ValueError("Amount must be non-negative"))
    if fields["recurrence_unit"] not in RECURRENCE_UNITS:
        raise InvalidDataException(ValueError(f"Invalid recurrence_unit: {fields['recurrence_unit']}"))
    if int(fields["recurrence_count"]) <= 0:
        raise InvalidDataException(ValueError("recurrence_count must be positive"))
    _require_currency(cursor, fields["currency_code"])
    _require_owned_account(cursor, user_id, fields.get("account_id"))
    _require_accessible_category(cursor, user_id, fields.get("category_id"))


def list_series(user_id, page: int, page_size: int, include_inactive: bool = False) -> tuple[list[dict], dict]:
    def work(cursor):
        query = "SELECT * FROM dompet.bill_series WHERE user_id = %s"
        params = [str(user_id)]
        if not include_inactive:
            query += " AND is_active = TRUE"
        query += " ORDER BY name"
        return paginate(cursor, query, params, page, page_size)

    return run_atomic(work, user_id=user_id)


def get_series(user_id, series_id) -> dict:
    def work(cursor):
        cursor.execute(
            "SELECT * FROM dompet.bill_series WHERE id = %s AND user_id = %s",
            (str(series_id), str(user_id)),
        )
        row = cursor.fetchone()
        if not row:
            raise NotFoundException(ValueError(f"Bill series not found: {series_id}"))
        return row

    return run_atomic(work, user_id=user_id)


def create_series(user_id, body: dict) -> dict:
    missing = [f for f in CREATE_REQUIRED_FIELDS if body.get(f) in (None, "")]
    if missing:
        raise InvalidDataException(ValueError(f"Missing required fields: {', '.join(missing)}"))

    fields = {field: body[field] for field in CREATE_REQUIRED_FIELDS}
    fields["category_id"] = body.get("category_id")
    fields["account_id"] = body.get("account_id")

    def work(cursor):
        _validate_fields(cursor, user_id, fields)
        cursor.execute(
            """
            INSERT INTO dompet.bill_series
                (user_id, name, amount, currency_code, category_id, account_id,
                 recurrence_unit, recurrence_count, anchor_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (
                str(user_id), fields["name"], fields["amount"], fields["currency_code"],
                fields["category_id"], fields["account_id"],
                fields["recurrence_unit"], fields["recurrence_count"], fields["anchor_date"],
            ),
        )
        row = cursor.fetchone()
        record_operation(cursor, "bill_series", row["id"], user_id, "CREATE", None, row_to_dict(row))

        # Materialize the first occurrence immediately, so it shows up in
        # GET /bills right away instead of waiting for the next on-demand
        # sync -- harmless to also backfill any other series here too.
        sync_bills(cursor, user_id)
        return row

    return run_atomic(work, user_id=user_id)


def update_series(user_id, series_id, body: dict) -> dict:
    """Only affects occurrences generated after the edit -- past/current
    occurrences already have their own copy of name/amount/etc. and are
    never rewritten (see dompet.bills' own comment)."""
    patch = {k: v for k, v in body.items() if k in UPDATABLE_FIELDS}
    if not patch:
        raise InvalidDataException(ValueError("No updatable fields provided"))

    def work(cursor):
        cursor.execute(
            "SELECT * FROM dompet.bill_series WHERE id = %s AND user_id = %s FOR UPDATE",
            (str(series_id), str(user_id)),
        )
        before = cursor.fetchone()
        if not before:
            raise NotFoundException(ValueError(f"Bill series not found: {series_id}"))

        merged = {field: patch.get(field, before[field]) for field in UPDATABLE_FIELDS}
        _validate_fields(cursor, user_id, merged)

        cursor.execute(
            """
            UPDATE dompet.bill_series
            SET name = %s, amount = %s, currency_code = %s, category_id = %s, account_id = %s,
                recurrence_unit = %s, recurrence_count = %s, updated_at = NOW()
            WHERE id = %s AND user_id = %s
            RETURNING *
            """,
            (
                merged["name"], merged["amount"], merged["currency_code"], merged["category_id"],
                merged["account_id"], merged["recurrence_unit"], merged["recurrence_count"],
                str(series_id), str(user_id),
            ),
        )
        after = cursor.fetchone()
        record_operation(cursor, "bill_series", series_id, user_id, "UPDATE", row_to_dict(before), row_to_dict(after))
        return after

    return run_atomic(work, user_id=user_id)


def deactivate_series(user_id, series_id) -> dict:
    """Stops future occurrences from being generated; existing ones (paid
    or not) are untouched."""
    def work(cursor):
        cursor.execute(
            "SELECT * FROM dompet.bill_series WHERE id = %s AND user_id = %s FOR UPDATE",
            (str(series_id), str(user_id)),
        )
        before = cursor.fetchone()
        if not before:
            raise NotFoundException(ValueError(f"Bill series not found: {series_id}"))

        cursor.execute(
            "UPDATE dompet.bill_series SET is_active = FALSE, updated_at = NOW() WHERE id = %s AND user_id = %s RETURNING *",
            (str(series_id), str(user_id)),
        )
        after = cursor.fetchone()
        record_operation(cursor, "bill_series", series_id, user_id, "DEACTIVATE", row_to_dict(before), row_to_dict(after))
        return after

    return run_atomic(work, user_id=user_id)
