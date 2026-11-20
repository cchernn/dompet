import uuid
from decimal import Decimal, InvalidOperation

from ..lib.exceptions import InvalidDataException, NotFoundException
from ..utils.db import run_atomic, paginate
from .operations import row_to_dict, record_operation
from .transaction_operation import (
    TRANSACTION_TYPES,
    _has_timezone_offset,
    _require_accessible_category,
    _require_accessible_location,
    _require_currency,
    _require_owned_account,
    create_transaction_in,
)

# Everything a draft can hold directly; all optional until approval.
STAGE_FIELDS = (
    "name", "type", "amount", "currency_code", "category_id",
    "source_account_id", "destination_account_id",
    "source_location_id", "destination_location_id", "datetime", "notes",
)

# Origins a caller may set. 'import' exists in the schema but is reserved
# for a later phase, so it isn't accepted over the API yet.
SETTABLE_ORIGINS = ("manual", "suggestion")

# Request-body key -> (link table, link column, how to validate each id).
# Sent as full lists; a key that is present replaces that set wholesale, a
# key that is absent leaves it alone.
LINKS = {
    "tag_ids": ("staged_transaction_tags", "tag_id", "transaction_tags"),
    "budget_ids": ("staged_transaction_budgets", "budget_id", "transaction_budgets"),
    "attachment_ids": ("staged_transaction_attachments", "attachment_id", "transaction_attachments"),
}

_LINK_VALIDATION = {
    "tag_ids": (
        "SELECT id FROM dompet.tags WHERE id = ANY(%s::uuid[]) AND user_id = %s AND is_active = TRUE",
        "Unknown, inactive, or not-owned tag",
    ),
    "budget_ids": (
        """
        SELECT b.id FROM dompet.budgets b
        JOIN dompet.budget_members bm ON bm.budget_id = b.id
        WHERE b.id = ANY(%s::uuid[]) AND b.is_active = TRUE AND bm.user_id = %s
        """,
        "Unknown, inactive, or inaccessible budget",
    ),
    "attachment_ids": (
        "SELECT id FROM dompet.attachments WHERE id = ANY(%s::uuid[]) AND user_id = %s AND is_active = TRUE",
        "Unknown, inactive, or not-owned attachment",
    ),
}


def _clean_ids(key: str, value) -> list[str]:
    if not isinstance(value, list):
        raise InvalidDataException(ValueError(f"{key} must be a list of ids"))
    cleaned = []
    for item in value:
        try:
            cleaned.append(str(uuid.UUID(str(item))))
        except ValueError:
            raise InvalidDataException(ValueError(f"{key} contains an invalid id: {item}"))
    return list(dict.fromkeys(cleaned))


def _require_valid_links(cursor, user_id, key: str, ids: list[str]) -> None:
    if not ids:
        return
    query, message = _LINK_VALIDATION[key]
    cursor.execute(query, (ids, str(user_id)))
    found = {str(row["id"]) for row in cursor.fetchall()}
    missing = [i for i in ids if i not in found]
    if missing:
        raise InvalidDataException(ValueError(f"{message}: {', '.join(missing)}"))


def _validate_draft(cursor, user_id, fields: dict) -> None:
    """Validates only what is filled in -- a draft may be incomplete, so a
    missing field is never an error here (approval checks for those)."""
    if fields.get("name") is not None and len(fields["name"]) > 255:
        raise InvalidDataException(ValueError("name must be at most 255 characters"))
    if fields.get("type") is not None and fields["type"] not in TRANSACTION_TYPES:
        raise InvalidDataException(ValueError(f"Invalid transaction type: {fields['type']}"))
    if fields.get("amount") is not None:
        try:
            amount = Decimal(str(fields["amount"]))
        except InvalidOperation:
            raise InvalidDataException(ValueError(f"amount must be a number: {fields['amount']}"))
        if amount < 0:
            raise InvalidDataException(ValueError("Amount must be non-negative"))
    if fields.get("datetime") is not None and not _has_timezone_offset(fields["datetime"]):
        raise InvalidDataException(ValueError(
            "datetime must include an explicit timezone offset (e.g. a trailing 'Z' or '+08:00')"
        ))

    if fields.get("currency_code") is not None:
        _require_currency(cursor, fields["currency_code"])
    for field in ("source_account_id", "destination_account_id"):
        if fields.get(field) is not None:
            _require_owned_account(cursor, user_id, fields[field], field)
    _require_accessible_category(cursor, user_id, fields.get("category_id"))

    # A location is only valid relative to its own leg's account, so it
    # can't be set before that account is.
    for location_field, account_field in (
        ("source_location_id", "source_account_id"),
        ("destination_location_id", "destination_account_id"),
    ):
        if fields.get(location_field) is not None:
            if fields.get(account_field) is None:
                raise InvalidDataException(ValueError(f"{account_field} is required when {location_field} is set"))
            _require_accessible_location(cursor, fields[location_field], fields[account_field], account_field)


def _read_links(cursor, staged_id) -> dict:
    links = {}
    for key, (table, column, _) in LINKS.items():
        cursor.execute(
            f"SELECT {column} FROM dompet.{table} WHERE staged_transaction_id = %s ORDER BY created_at, {column}",
            (str(staged_id),),
        )
        links[key] = [str(row[column]) for row in cursor.fetchall()]
    return links


def _replace_links(cursor, user_id, staged_id, body: dict) -> None:
    for key, (table, column, _) in LINKS.items():
        if key not in body:
            continue
        ids = _clean_ids(key, body[key])
        _require_valid_links(cursor, user_id, key, ids)
        cursor.execute(f"DELETE FROM dompet.{table} WHERE staged_transaction_id = %s", (str(staged_id),))
        for item in ids:
            cursor.execute(
                f"INSERT INTO dompet.{table} (staged_transaction_id, {column}) VALUES (%s, %s)",
                (str(staged_id), item),
            )


def _copy_links_from_transaction(cursor, user_id, staged_id, transaction_id) -> None:
    """Carries a source transaction's tags and budgets onto a draft staged
    from it, skipping any that are no longer usable. Attachments are left
    behind on purpose -- a receipt belongs to the one purchase, not to the
    pattern."""
    cursor.execute(
        """
        INSERT INTO dompet.staged_transaction_tags (staged_transaction_id, tag_id)
        SELECT %s, tt.tag_id FROM dompet.transaction_tags tt
        JOIN dompet.tags g ON g.id = tt.tag_id AND g.is_active = TRUE AND g.user_id = %s
        WHERE tt.transaction_id = %s
        ON CONFLICT DO NOTHING
        """,
        (str(staged_id), str(user_id), str(transaction_id)),
    )
    cursor.execute(
        """
        INSERT INTO dompet.staged_transaction_budgets (staged_transaction_id, budget_id)
        SELECT %s, tb.budget_id FROM dompet.transaction_budgets tb
        JOIN dompet.budgets b ON b.id = tb.budget_id AND b.is_active = TRUE
        JOIN dompet.budget_members bm ON bm.budget_id = b.id AND bm.user_id = %s
        WHERE tb.transaction_id = %s
        ON CONFLICT DO NOTHING
        """,
        (str(staged_id), str(user_id), str(transaction_id)),
    )


def _with_links(cursor, row) -> dict:
    return {**dict(row), **_read_links(cursor, row["id"])}


def _lock_owned_staged(cursor, user_id, staged_id) -> dict:
    cursor.execute(
        "SELECT * FROM dompet.staged_transactions WHERE id = %s AND user_id = %s FOR UPDATE",
        (str(staged_id), str(user_id)),
    )
    row = cursor.fetchone()
    if not row:
        raise NotFoundException(ValueError(f"Staged transaction not found: {staged_id}"))
    return row


def _require_draft(row) -> None:
    if row["status"] != "draft":
        raise InvalidDataException(ValueError(f"Staged transaction is already {row['status']}"))


def list_staged(user_id, page: int, page_size: int, status: str = "draft") -> tuple[list[dict], dict]:
    def work(cursor):
        query = "SELECT * FROM dompet.staged_transactions WHERE user_id = %s"
        params = [str(user_id)]
        if status:
            query += " AND status = %s"
            params.append(status)
        query += " ORDER BY created_at DESC"
        return paginate(cursor, query, params, page, page_size)

    return run_atomic(work, user_id=user_id)


def get_staged(user_id, staged_id) -> dict:
    def work(cursor):
        cursor.execute(
            "SELECT * FROM dompet.staged_transactions WHERE id = %s AND user_id = %s",
            (str(staged_id), str(user_id)),
        )
        row = cursor.fetchone()
        if not row:
            raise NotFoundException(ValueError(f"Staged transaction not found: {staged_id}"))
        return _with_links(cursor, row)

    return run_atomic(work, user_id=user_id)


def create_staged(user_id, body: dict) -> dict:
    fields = {field: body.get(field) for field in STAGE_FIELDS}
    origin_transaction_id = body.get("origin_transaction_id")
    origin = body.get("origin") or ("suggestion" if origin_transaction_id else "manual")
    if origin not in SETTABLE_ORIGINS:
        raise InvalidDataException(ValueError(f"Invalid origin: {origin}"))

    def work(cursor):
        _validate_draft(cursor, user_id, fields)
        if origin_transaction_id is not None:
            cursor.execute(
                "SELECT 1 FROM dompet.transactions WHERE id = %s AND user_id = %s",
                (str(origin_transaction_id), str(user_id)),
            )
            if not cursor.fetchone():
                raise InvalidDataException(
                    ValueError(f"Unknown or not-owned origin_transaction_id: {origin_transaction_id}")
                )

        cursor.execute(
            """
            INSERT INTO dompet.staged_transactions
                (user_id, origin, origin_transaction_id, name, type, amount, currency_code,
                 category_id, source_account_id, destination_account_id,
                 source_location_id, destination_location_id, datetime, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (
                str(user_id), origin, origin_transaction_id, fields["name"], fields["type"],
                fields["amount"], fields["currency_code"], fields["category_id"],
                fields["source_account_id"], fields["destination_account_id"],
                fields["source_location_id"], fields["destination_location_id"],
                fields["datetime"], fields["notes"],
            ),
        )
        row = cursor.fetchone()
        _replace_links(cursor, user_id, row["id"], body)
        if origin_transaction_id is not None and not any(key in body for key in LINKS):
            # Staged from a suggestion with no explicit lists: inherit the
            # source transaction's tags and budgets.
            _copy_links_from_transaction(cursor, user_id, row["id"], origin_transaction_id)
        after = _with_links(cursor, row)
        record_operation(cursor, "staged_transaction", row["id"], user_id, "CREATE", None, row_to_dict(after))
        return after

    return run_atomic(work, user_id=user_id)


def update_staged(user_id, staged_id, body: dict) -> dict:
    patch = {k: body[k] for k in STAGE_FIELDS if k in body}
    if not patch and not any(key in body for key in LINKS):
        raise InvalidDataException(ValueError("No updatable fields provided"))

    def work(cursor):
        before_row = _lock_owned_staged(cursor, user_id, staged_id)
        _require_draft(before_row)
        before = row_to_dict(_with_links(cursor, before_row))

        merged = {field: patch.get(field, before_row[field]) for field in STAGE_FIELDS}
        _validate_draft(cursor, user_id, merged)

        cursor.execute(
            """
            UPDATE dompet.staged_transactions
            SET name = %s, type = %s, amount = %s, currency_code = %s, category_id = %s,
                source_account_id = %s, destination_account_id = %s,
                source_location_id = %s, destination_location_id = %s,
                datetime = %s, notes = %s, updated_at = NOW()
            WHERE id = %s AND user_id = %s
            RETURNING *
            """,
            (
                merged["name"], merged["type"], merged["amount"], merged["currency_code"],
                merged["category_id"], merged["source_account_id"], merged["destination_account_id"],
                merged["source_location_id"], merged["destination_location_id"],
                merged["datetime"], merged["notes"], str(staged_id), str(user_id),
            ),
        )
        row = cursor.fetchone()
        _replace_links(cursor, user_id, staged_id, body)
        after = _with_links(cursor, row)
        record_operation(cursor, "staged_transaction", staged_id, user_id, "UPDATE", before, row_to_dict(after))
        return after

    return run_atomic(work, user_id=user_id)


def discard_staged(user_id, staged_id) -> dict:
    def work(cursor):
        before_row = _lock_owned_staged(cursor, user_id, staged_id)
        _require_draft(before_row)
        before = row_to_dict(_with_links(cursor, before_row))

        cursor.execute(
            "UPDATE dompet.staged_transactions SET status = 'discarded', updated_at = NOW() "
            "WHERE id = %s AND user_id = %s RETURNING *",
            (str(staged_id), str(user_id)),
        )
        after = _with_links(cursor, cursor.fetchone())
        record_operation(cursor, "staged_transaction", staged_id, user_id, "DEACTIVATE", before, row_to_dict(after))
        return after

    return run_atomic(work, user_id=user_id)


def approve_staged(user_id, staged_id, body: dict = None) -> dict:
    """Turns a draft into a real transaction through the same create logic
    as the add flow, copies its tag/budget/attachment links across, and
    marks the draft approved -- all in one database transaction, so a
    failure anywhere leaves the draft untouched. A `datetime` (or `date`) in
    the request body overrides the draft's own, for approving a draft that
    was staged without one. Returns the new transaction."""
    body = body or {}

    def work(cursor):
        before_row = _lock_owned_staged(cursor, user_id, staged_id)
        _require_draft(before_row)
        before = row_to_dict(_with_links(cursor, before_row))
        links = _read_links(cursor, staged_id)

        transaction_body = {field: before_row[field] for field in STAGE_FIELDS if field != "notes"}
        if body.get("datetime") or body.get("date"):
            transaction_body["datetime"] = body.get("datetime")
            transaction_body["date"] = body.get("date")

        missing = [
            f for f in ("name", "type", "amount", "currency_code", "source_account_id", "destination_account_id")
            if transaction_body.get(f) in (None, "")
        ]
        if not transaction_body.get("datetime") and not transaction_body.get("date"):
            missing.append("datetime")
        if missing:
            raise InvalidDataException(ValueError(f"Cannot approve, missing: {', '.join(missing)}"))

        # Revalidated now, not trusted from staging time -- a tag or budget
        # may have been deactivated since the draft was saved.
        for key, ids in links.items():
            _require_valid_links(cursor, user_id, key, ids)

        transaction = create_transaction_in(
            cursor, user_id, transaction_body, {"staged_transaction_id": str(staged_id)}
        )

        for key, (_, column, target_table) in LINKS.items():
            for item in links[key]:
                cursor.execute(
                    f"INSERT INTO dompet.{target_table} (transaction_id, {column}) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (transaction["id"], item),
                )

        cursor.execute(
            "UPDATE dompet.staged_transactions SET status = 'approved', approved_transaction_id = %s, "
            "updated_at = NOW() WHERE id = %s AND user_id = %s RETURNING *",
            (transaction["id"], str(staged_id), str(user_id)),
        )
        after = _with_links(cursor, cursor.fetchone())
        record_operation(
            cursor, "staged_transaction", staged_id, user_id, "UPDATE", before, row_to_dict(after),
            {"approved_transaction_id": transaction["id"]},
        )
        return transaction

    return run_atomic(work, user_id=user_id)
