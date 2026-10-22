from datetime import date

from ..lib.exceptions import InvalidDataException, NotFoundException
from ..utils.db import run_atomic, paginate

UPDATABLE_FIELDS = ("transaction_id", "amount_paid", "paid_date", "notes")


def _require_owned_bill(cursor, user_id, bill_id) -> dict:
    cursor.execute(
        "SELECT * FROM dompet.bills WHERE id = %s AND user_id = %s",
        (str(bill_id), str(user_id)),
    )
    row = cursor.fetchone()
    if not row:
        raise NotFoundException(ValueError(f"Bill not found: {bill_id}"))
    return row


def _require_owned_transaction(cursor, user_id, transaction_id) -> dict:
    cursor.execute(
        "SELECT * FROM dompet.transactions WHERE id = %s AND user_id = %s",
        (str(transaction_id), str(user_id)),
    )
    row = cursor.fetchone()
    if not row:
        raise NotFoundException(ValueError(f"Transaction not found or not owned by user: {transaction_id}"))
    return row


def list_payments(user_id, bill_id, page: int, page_size: int) -> tuple[list[dict], dict]:
    def work(cursor):
        _require_owned_bill(cursor, user_id, bill_id)
        query = "SELECT * FROM dompet.bill_payments WHERE bill_id = %s ORDER BY paid_date DESC, created_at DESC"
        return paginate(cursor, query, [str(bill_id)], page, page_size)

    return run_atomic(work, user_id=user_id)


def create_payment(user_id, bill_id, body: dict) -> dict:
    transaction_id = body.get("transaction_id")

    def work(cursor):
        bill = _require_owned_bill(cursor, user_id, bill_id)
        transaction = _require_owned_transaction(cursor, user_id, transaction_id) if transaction_id else None

        amount_paid = body.get("amount_paid")
        if amount_paid is None:
            amount_paid = bill["amount"]
        elif float(amount_paid) < 0:
            raise InvalidDataException(ValueError("amount_paid must be non-negative"))

        paid_date = body.get("paid_date")
        if paid_date is None:
            paid_date = transaction["datetime"].date().isoformat() if transaction else date.today().isoformat()

        cursor.execute(
            """
            INSERT INTO dompet.bill_payments (user_id, bill_id, transaction_id, amount_paid, paid_date, notes)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (str(user_id), str(bill_id), str(transaction_id) if transaction_id else None,
             amount_paid, paid_date, body.get("notes")),
        )
        return cursor.fetchone()

    return run_atomic(work, user_id=user_id)


def update_payment(user_id, bill_id, payment_id, body: dict) -> dict:
    """Lets a payment be edited in place -- most notably, setting
    transaction_id to null unlinks the transaction while keeping the
    amount/date/notes already recorded, instead of having to delete the
    payment and recreate it from scratch."""
    patch = {k: v for k, v in body.items() if k in UPDATABLE_FIELDS}
    if not patch:
        raise InvalidDataException(ValueError("No updatable fields provided"))

    def work(cursor):
        _require_owned_bill(cursor, user_id, bill_id)
        cursor.execute(
            "SELECT * FROM dompet.bill_payments WHERE id = %s AND bill_id = %s AND user_id = %s FOR UPDATE",
            (str(payment_id), str(bill_id), str(user_id)),
        )
        before = cursor.fetchone()
        if not before:
            raise NotFoundException(ValueError(f"Bill payment not found: {payment_id}"))

        merged = {field: patch.get(field, before[field]) for field in UPDATABLE_FIELDS}

        if merged["transaction_id"]:
            _require_owned_transaction(cursor, user_id, merged["transaction_id"])
        if float(merged["amount_paid"]) < 0:
            raise InvalidDataException(ValueError("amount_paid must be non-negative"))

        cursor.execute(
            """
            UPDATE dompet.bill_payments
            SET transaction_id = %s, amount_paid = %s, paid_date = %s, notes = %s
            WHERE id = %s AND bill_id = %s AND user_id = %s
            RETURNING *
            """,
            (
                str(merged["transaction_id"]) if merged["transaction_id"] else None,
                merged["amount_paid"], merged["paid_date"], merged["notes"],
                str(payment_id), str(bill_id), str(user_id),
            ),
        )
        return cursor.fetchone()

    return run_atomic(work, user_id=user_id)


def delete_payment(user_id, bill_id, payment_id) -> dict:
    def work(cursor):
        _require_owned_bill(cursor, user_id, bill_id)
        cursor.execute(
            "DELETE FROM dompet.bill_payments WHERE id = %s AND bill_id = %s AND user_id = %s RETURNING *",
            (str(payment_id), str(bill_id), str(user_id)),
        )
        row = cursor.fetchone()
        if not row:
            raise NotFoundException(ValueError(f"Bill payment not found: {payment_id}"))
        return row

    return run_atomic(work, user_id=user_id)
