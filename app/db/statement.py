from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from ..lib.exceptions import InvalidDataException, NotFoundException
from ..utils.db import run_atomic, paginate
from .operations import row_to_dict, record_operation
from .notification import MAX_NOTIFICATIONS_PER_USER
from .bill import _advance_date

CREATE_REQUIRED_FIELDS = ("account_id", "statement_date", "period_start", "period_end")
UPDATABLE_FIELDS = (
    "statement_date", "period_start", "period_end", "received_date",
    "opening_balance", "closing_balance", "currency_code", "notes",
)

# Caps how many missing occurrences one sync call will backfill for a single
# series, so a daily series anchored years in the past can't turn one
# request into thousands of inserts -- any remainder just gets picked up by
# the next on-demand sync.
MAX_OCCURRENCES_PER_SYNC = 365

# Hard stop on the date-walk itself (which only computes dates, no inserts),
# in case a long-running short-interval series has a huge backlog of
# already-materialized occurrences to skip over.
MAX_DATE_STEPS = 20000


def _require_currency(cursor, currency_code) -> None:
    if currency_code is None:
        return
    cursor.execute(
        "SELECT 1 FROM dompet.currencies WHERE code = %s AND is_active = TRUE",
        (currency_code,),
    )
    if not cursor.fetchone():
        raise InvalidDataException(ValueError(f"Unknown or inactive currency: {currency_code}"))


def _require_owned_account(cursor, user_id, account_id) -> None:
    cursor.execute(
        "SELECT 1 FROM dompet.accounts WHERE id = %s AND user_id = %s AND is_active = TRUE",
        (account_id, str(user_id)),
    )
    if not cursor.fetchone():
        raise InvalidDataException(ValueError(f"Unknown, inactive, or not-owned account: {account_id}"))


DATE_FIELDS = ("statement_date", "period_start", "period_end", "received_date")
BALANCE_FIELDS = ("opening_balance", "closing_balance")


def _normalize_fields(fields: dict) -> None:
    """Request bodies carry dates as ISO strings but rows read back from the
    database carry date objects -- convert in place so validation (and the
    merged-on-update case, which mixes the two) can compare them."""
    for field in DATE_FIELDS:
        value = fields.get(field)
        if value is None or isinstance(value, date):
            continue
        try:
            fields[field] = date.fromisoformat(str(value))
        except ValueError:
            raise InvalidDataException(ValueError(f"{field} must be an ISO date (YYYY-MM-DD): {value}"))
    for field in BALANCE_FIELDS:
        value = fields.get(field)
        if value is None:
            continue
        try:
            Decimal(str(value))
        except InvalidOperation:
            raise InvalidDataException(ValueError(f"{field} must be a number: {value}"))


def _validate_fields(cursor, user_id, fields: dict) -> None:
    _normalize_fields(fields)
    if fields["period_end"] < fields["period_start"]:
        raise InvalidDataException(ValueError("period_end must not be before period_start"))
    has_balance = fields.get("opening_balance") is not None or fields.get("closing_balance") is not None
    if has_balance and not fields.get("currency_code"):
        raise InvalidDataException(ValueError("currency_code is required when a balance is given"))
    _require_currency(cursor, fields.get("currency_code"))
    _require_owned_account(cursor, user_id, fields["account_id"])


def _generate_due_occurrences(cursor, user_id, series: dict, today: date) -> None:
    cursor.execute(
        "SELECT MAX(statement_date) AS max_statement_date FROM dompet.statements WHERE series_id = %s",
        (str(series["id"]),),
    )
    last_statement_date = cursor.fetchone()["max_statement_date"]

    unit, count, anchor = series["recurrence_unit"], series["recurrence_count"], series["anchor_date"]
    inserted = 0
    for k in range(MAX_DATE_STEPS):
        # Always measured from the fixed anchor, not from the previous
        # occurrence, so a monthly series on the 31st doesn't drift after
        # a short month.
        statement_date = _advance_date(anchor, unit, count * k)
        if statement_date > today or inserted >= MAX_OCCURRENCES_PER_SYNC:
            break
        if last_statement_date is not None and statement_date <= last_statement_date:
            continue
        # Starts the day after the previous occurrence, measured from the
        # anchor like every other date here -- stepping back from this
        # statement_date instead would leave a gap or overlap after a short
        # month (Sep 30 minus a month is Aug 30, not Aug 31).
        period_start = _advance_date(anchor, unit, count * (k - 1)) + timedelta(days=1)
        # No conflict target: this also skips a period the user already
        # entered by hand (statements_account_period_unique), not just a
        # repeat of the same series occurrence.
        cursor.execute(
            """
            INSERT INTO dompet.statements
                (user_id, series_id, account_id, statement_date, period_start, period_end, currency_code)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            (
                str(user_id), str(series["id"]), str(series["account_id"]),
                statement_date, period_start, statement_date, series["currency_code"],
            ),
        )
        inserted += 1


def _sync_statement_notifications(cursor, user_id, today: date) -> None:
    cursor.execute(
        """
        SELECT s.id, s.statement_date, s.period_end, a.name AS account_name
        FROM dompet.statements s
        JOIN dompet.accounts a ON a.id = s.account_id
        WHERE s.user_id = %s AND s.is_active = TRUE
          AND s.received_date IS NULL AND s.statement_date < %s
        """,
        (str(user_id), today),
    )
    overdue = cursor.fetchall()
    if not overdue:
        return

    created_any = False
    for statement in overdue:
        cursor.execute(
            """
            SELECT 1 FROM dompet.notifications
            WHERE user_id = %s AND entity_type = 'statement' AND entity_id = %s AND type = 'warning'
            """,
            (str(user_id), str(statement["id"])),
        )
        if cursor.fetchone():
            continue
        message = (
            f"Statement for '{statement['account_name']}' (period ending {statement['period_end'].isoformat()}) "
            f"has not been received (expected {statement['statement_date'].isoformat()})"
        )
        cursor.execute(
            """
            INSERT INTO dompet.notifications (user_id, type, message, entity_type, entity_id)
            VALUES (%s, 'warning', %s, 'statement', %s)
            """,
            (str(user_id), message, str(statement["id"])),
        )
        created_any = True

    if created_any:
        cursor.execute(
            """
            DELETE FROM dompet.notifications
            WHERE user_id = %s AND id NOT IN (
                SELECT id FROM dompet.notifications WHERE user_id = %s
                ORDER BY created_at DESC LIMIT %s
            )
            """,
            (str(user_id), str(user_id), MAX_NOTIFICATIONS_PER_USER),
        )


def sync_statements(cursor, user_id) -> None:
    """Lazily materializes any occurrences a statement series should have by
    now, and raises an overdue notification for statements not yet received
    -- the on-demand replacement for a scheduled job, same as sync_bills.
    Called at the top of every statement/notification read, not on writes."""
    today = date.today()
    cursor.execute(
        "SELECT * FROM dompet.statement_series WHERE user_id = %s AND is_active = TRUE",
        (str(user_id),),
    )
    for series in cursor.fetchall():
        _generate_due_occurrences(cursor, user_id, series, today)
    _sync_statement_notifications(cursor, user_id, today)


def list_statements(user_id, page: int, page_size: int, include_inactive: bool = False) -> tuple[list[dict], dict]:
    def work(cursor):
        sync_statements(cursor, user_id)
        query = "SELECT * FROM dompet.statements WHERE user_id = %s"
        params = [str(user_id)]
        if not include_inactive:
            query += " AND is_active = TRUE"
        query += " ORDER BY statement_date DESC, created_at DESC"
        return paginate(cursor, query, params, page, page_size)

    return run_atomic(work, user_id=user_id)


def get_statement(user_id, statement_id) -> dict:
    def work(cursor):
        sync_statements(cursor, user_id)
        cursor.execute(
            "SELECT * FROM dompet.statements WHERE id = %s AND user_id = %s",
            (str(statement_id), str(user_id)),
        )
        row = cursor.fetchone()
        if not row:
            raise NotFoundException(ValueError(f"Statement not found: {statement_id}"))
        return row

    return run_atomic(work, user_id=user_id)


def create_statement(user_id, body: dict) -> dict:
    missing = [f for f in CREATE_REQUIRED_FIELDS if body.get(f) in (None, "")]
    if missing:
        raise InvalidDataException(ValueError(f"Missing required fields: {', '.join(missing)}"))

    fields = {field: body[field] for field in CREATE_REQUIRED_FIELDS}
    for field in UPDATABLE_FIELDS:
        fields.setdefault(field, body.get(field))

    def work(cursor):
        _validate_fields(cursor, user_id, fields)
        cursor.execute(
            """
            INSERT INTO dompet.statements
                (user_id, series_id, account_id, statement_date, period_start, period_end, received_date,
                 opening_balance, closing_balance, currency_code, notes)
            VALUES (%s, NULL, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (
                str(user_id), fields["account_id"], fields["statement_date"], fields["period_start"],
                fields["period_end"], fields["received_date"], fields["opening_balance"],
                fields["closing_balance"], fields["currency_code"], fields["notes"],
            ),
        )
        row = cursor.fetchone()
        record_operation(cursor, "statement", row["id"], user_id, "CREATE", None, row_to_dict(row))
        return row

    return run_atomic(work, user_id=user_id)


def update_statement(user_id, statement_id, body: dict) -> dict:
    patch = {k: v for k, v in body.items() if k in UPDATABLE_FIELDS}
    if not patch:
        raise InvalidDataException(ValueError("No updatable fields provided"))

    def work(cursor):
        cursor.execute(
            "SELECT * FROM dompet.statements WHERE id = %s AND user_id = %s FOR UPDATE",
            (str(statement_id), str(user_id)),
        )
        before = cursor.fetchone()
        if not before:
            raise NotFoundException(ValueError(f"Statement not found: {statement_id}"))

        merged = {field: patch.get(field, before[field]) for field in UPDATABLE_FIELDS}
        merged["account_id"] = before["account_id"]
        _validate_fields(cursor, user_id, merged)

        cursor.execute(
            """
            UPDATE dompet.statements
            SET statement_date = %s, period_start = %s, period_end = %s, received_date = %s,
                opening_balance = %s, closing_balance = %s, currency_code = %s, notes = %s,
                updated_at = NOW()
            WHERE id = %s AND user_id = %s
            RETURNING *
            """,
            (
                merged["statement_date"], merged["period_start"], merged["period_end"], merged["received_date"],
                merged["opening_balance"], merged["closing_balance"], merged["currency_code"], merged["notes"],
                str(statement_id), str(user_id),
            ),
        )
        after = cursor.fetchone()
        record_operation(cursor, "statement", statement_id, user_id, "UPDATE", row_to_dict(before), row_to_dict(after))
        return after

    return run_atomic(work, user_id=user_id)


def deactivate_statement(user_id, statement_id) -> dict:
    def work(cursor):
        cursor.execute(
            "SELECT * FROM dompet.statements WHERE id = %s AND user_id = %s FOR UPDATE",
            (str(statement_id), str(user_id)),
        )
        before = cursor.fetchone()
        if not before:
            raise NotFoundException(ValueError(f"Statement not found: {statement_id}"))

        cursor.execute(
            "UPDATE dompet.statements SET is_active = FALSE, updated_at = NOW() WHERE id = %s AND user_id = %s RETURNING *",
            (str(statement_id), str(user_id)),
        )
        after = cursor.fetchone()
        record_operation(cursor, "statement", statement_id, user_id, "DEACTIVATE", row_to_dict(before), row_to_dict(after))
        return after

    return run_atomic(work, user_id=user_id)
