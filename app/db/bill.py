import calendar
from datetime import date, timedelta

from ..lib.exceptions import InvalidDataException, NotFoundException
from ..utils.db import run_atomic, paginate
from .operations import row_to_dict, record_operation
from .notification import MAX_NOTIFICATIONS_PER_USER

CREATE_REQUIRED_FIELDS = ("name", "amount", "currency_code", "bill_date")
UPDATABLE_FIELDS = ("name", "amount", "currency_code", "category_id", "account_id", "bill_date", "due_date")

# How far ahead of due_date a "due soon" notification fires.
NOTIFY_DAYS_BEFORE = 3

# Caps how many missing occurrences one sync call will backfill for a single
# series, so a daily bill anchored years in the past can't turn one request
# into thousands of inserts -- any remainder just gets picked up by the next
# on-demand sync.
MAX_OCCURRENCES_PER_SYNC = 365


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
    _require_currency(cursor, fields["currency_code"])
    _require_owned_account(cursor, user_id, fields.get("account_id"))
    _require_accessible_category(cursor, user_id, fields.get("category_id"))


def _add_months(d: date, months: int) -> date:
    total = d.month - 1 + months
    year = d.year + total // 12
    month = total % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _advance_date(d: date, unit: str, count: int) -> date:
    if unit == "day":
        return d + timedelta(days=count)
    if unit == "week":
        return d + timedelta(weeks=count)
    if unit == "month":
        return _add_months(d, count)
    if unit == "year":
        return _add_months(d, count * 12)
    raise ValueError(f"Unknown recurrence_unit: {unit}")


def _generate_due_occurrences(cursor, user_id, series: dict, today: date) -> None:
    cursor.execute(
        "SELECT MAX(bill_date) AS max_bill_date FROM dompet.bills WHERE series_id = %s",
        (str(series["id"]),),
    )
    last_bill_date = cursor.fetchone()["max_bill_date"]
    next_bill_date = series["anchor_date"] if last_bill_date is None else _advance_date(
        last_bill_date, series["recurrence_unit"], series["recurrence_count"]
    )

    for _ in range(MAX_OCCURRENCES_PER_SYNC):
        if next_bill_date > today:
            break
        # due_date is the day before the *next* occurrence's bill_date --
        # computed directly from the fixed recurrence rule, not by looking
        # ahead at an actual generated row, so it doesn't depend on
        # generation order.
        due_date = _advance_date(
            next_bill_date, series["recurrence_unit"], series["recurrence_count"]
        ) - timedelta(days=1)
        cursor.execute(
            """
            INSERT INTO dompet.bills
                (user_id, series_id, name, amount, currency_code, category_id, account_id, bill_date, due_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (series_id, bill_date) WHERE series_id IS NOT NULL DO NOTHING
            RETURNING id
            """,
            (
                str(user_id), str(series["id"]), series["name"], series["amount"], series["currency_code"],
                series["category_id"], series["account_id"], next_bill_date, due_date,
            ),
        )
        new_bill = cursor.fetchone()
        if new_bill:
            # Linking a bill to a budget fans out to every occurrence in its
            # series (see bill_budget.link_budget) -- a newly generated
            # occurrence needs the same links copied forward, otherwise it
            # silently falls outside the budget the rest of the series is
            # shared through.
            cursor.execute(
                """
                INSERT INTO dompet.bill_budgets (bill_id, budget_id)
                SELECT %s, bb.budget_id
                FROM dompet.bill_budgets bb
                JOIN dompet.bills b ON b.id = bb.bill_id
                WHERE b.series_id = %s
                ON CONFLICT DO NOTHING
                """,
                (str(new_bill["id"]), str(series["id"])),
            )
        next_bill_date = _advance_date(next_bill_date, series["recurrence_unit"], series["recurrence_count"])


def _sync_bill_notifications(cursor, user_id, today: date) -> None:
    cursor.execute(
        """
        SELECT b.id, b.name, b.due_date, b.amount,
               COALESCE(SUM(bp.amount_paid), 0.00) AS paid_amount
        FROM dompet.bills b
        LEFT JOIN dompet.bill_payments bp ON bp.bill_id = b.id
        WHERE b.user_id = %s AND b.is_active = TRUE AND b.due_date <= %s
        GROUP BY b.id, b.name, b.due_date, b.amount
        """,
        (str(user_id), today + timedelta(days=NOTIFY_DAYS_BEFORE)),
    )
    bills_due = cursor.fetchall()
    if not bills_due:
        return

    created_any = False
    for bill in bills_due:
        if bill["paid_amount"] >= bill["amount"]:
            continue
        notif_type = "error" if bill["due_date"] < today else "warning"
        cursor.execute(
            """
            SELECT 1 FROM dompet.notifications
            WHERE user_id = %s AND entity_type = 'bill' AND entity_id = %s AND type = %s
            """,
            (str(user_id), str(bill["id"]), notif_type),
        )
        if cursor.fetchone():
            continue
        message = (
            f"Bill '{bill['name']}' is overdue (was due {bill['due_date'].isoformat()})"
            if notif_type == "error"
            else f"Bill '{bill['name']}' is due on {bill['due_date'].isoformat()}"
        )
        cursor.execute(
            """
            INSERT INTO dompet.notifications (user_id, type, message, entity_type, entity_id)
            VALUES (%s, %s, %s, 'bill', %s)
            """,
            (str(user_id), notif_type, message, str(bill["id"])),
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


def sync_bills(cursor, user_id) -> None:
    """Lazily materializes any occurrences a recurring series should have by
    now, and raises due-soon/overdue notifications for unpaid bills -- the
    on-demand replacement for a scheduled job. Called at the top of every
    bill/notification read, not on writes."""
    today = date.today()
    cursor.execute(
        "SELECT * FROM dompet.bill_series WHERE user_id = %s AND is_active = TRUE",
        (str(user_id),),
    )
    for series in cursor.fetchall():
        _generate_due_occurrences(cursor, user_id, series, today)
    _sync_bill_notifications(cursor, user_id, today)


def list_bills(user_id, page: int, page_size: int, include_inactive: bool = False) -> tuple[list[dict], dict]:
    def work(cursor):
        sync_bills(cursor, user_id)
        query = "SELECT * FROM dompet.bills WHERE user_id = %s"
        params = [str(user_id)]
        if not include_inactive:
            query += " AND is_active = TRUE"
        query += " ORDER BY bill_date ASC, created_at ASC"
        return paginate(cursor, query, params, page, page_size)

    return run_atomic(work, user_id=user_id)


def get_bill(user_id, bill_id) -> dict:
    def work(cursor):
        sync_bills(cursor, user_id)
        cursor.execute(
            "SELECT * FROM dompet.bills WHERE id = %s AND user_id = %s",
            (str(bill_id), str(user_id)),
        )
        row = cursor.fetchone()
        if not row:
            raise NotFoundException(ValueError(f"Bill not found: {bill_id}"))
        return row

    return run_atomic(work, user_id=user_id)


def create_bill(user_id, body: dict) -> dict:
    missing = [f for f in CREATE_REQUIRED_FIELDS if body.get(f) in (None, "")]
    if missing:
        raise InvalidDataException(ValueError(f"Missing required fields: {', '.join(missing)}"))

    fields = {field: body[field] for field in CREATE_REQUIRED_FIELDS}
    fields["category_id"] = body.get("category_id")
    fields["account_id"] = body.get("account_id")
    # A one-off bill has no "next bill_date" to derive a due_date from --
    # default to the same day as bill_date unless given explicitly.
    fields["due_date"] = body.get("due_date") or fields["bill_date"]

    def work(cursor):
        _validate_fields(cursor, user_id, fields)
        cursor.execute(
            """
            INSERT INTO dompet.bills
                (user_id, series_id, name, amount, currency_code, category_id, account_id, bill_date, due_date)
            VALUES (%s, NULL, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (
                str(user_id), fields["name"], fields["amount"], fields["currency_code"],
                fields["category_id"], fields["account_id"], fields["bill_date"], fields["due_date"],
            ),
        )
        row = cursor.fetchone()
        record_operation(cursor, "bill", row["id"], user_id, "CREATE", None, row_to_dict(row))
        return row

    return run_atomic(work, user_id=user_id)


def update_bill(user_id, bill_id, body: dict) -> dict:
    patch = {k: v for k, v in body.items() if k in UPDATABLE_FIELDS}
    if not patch:
        raise InvalidDataException(ValueError("No updatable fields provided"))

    def work(cursor):
        cursor.execute(
            "SELECT * FROM dompet.bills WHERE id = %s AND user_id = %s FOR UPDATE",
            (str(bill_id), str(user_id)),
        )
        before = cursor.fetchone()
        if not before:
            raise NotFoundException(ValueError(f"Bill not found: {bill_id}"))

        merged = {field: patch.get(field, before[field]) for field in UPDATABLE_FIELDS}
        _validate_fields(cursor, user_id, merged)

        cursor.execute(
            """
            UPDATE dompet.bills
            SET name = %s, amount = %s, currency_code = %s, category_id = %s,
                account_id = %s, bill_date = %s, due_date = %s, updated_at = NOW()
            WHERE id = %s AND user_id = %s
            RETURNING *
            """,
            (
                merged["name"], merged["amount"], merged["currency_code"], merged["category_id"],
                merged["account_id"], merged["bill_date"], merged["due_date"], str(bill_id), str(user_id),
            ),
        )
        after = cursor.fetchone()
        record_operation(cursor, "bill", bill_id, user_id, "UPDATE", row_to_dict(before), row_to_dict(after))
        return after

    return run_atomic(work, user_id=user_id)


def deactivate_bill(user_id, bill_id) -> dict:
    def work(cursor):
        cursor.execute(
            "SELECT * FROM dompet.bills WHERE id = %s AND user_id = %s FOR UPDATE",
            (str(bill_id), str(user_id)),
        )
        before = cursor.fetchone()
        if not before:
            raise NotFoundException(ValueError(f"Bill not found: {bill_id}"))

        cursor.execute(
            "UPDATE dompet.bills SET is_active = FALSE, updated_at = NOW() WHERE id = %s AND user_id = %s RETURNING *",
            (str(bill_id), str(user_id)),
        )
        after = cursor.fetchone()
        record_operation(cursor, "bill", bill_id, user_id, "DEACTIVATE", row_to_dict(before), row_to_dict(after))
        return after

    return run_atomic(work, user_id=user_id)
