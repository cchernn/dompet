from ..utils.db import run_atomic, paginate, like_pattern
from ..lib.exceptions import InvalidDataException
from .bill import sync_bills

KINDS = ("series", "one_off")


def search_groups(
    user_id, page: int, page_size: int,
    q: str = None, kind: str = None, category: str = None, account: str = None,
    is_overdue: bool = None, include_paid: bool = False,
) -> tuple[list[dict], dict]:
    if kind is not None and kind not in KINDS:
        raise InvalidDataException(ValueError(f"Invalid kind: {kind}"))

    def work(cursor):
        sync_bills(cursor, user_id)

        query = "SELECT * FROM dompet.vw_bill_groups WHERE user_id = %s"
        params = [str(user_id)]
        if q:
            query += " AND name ILIKE %s"
            params.append(like_pattern(q))
        if kind:
            query += " AND kind = %s"
            params.append(kind)
        if category:
            query += " AND category = %s"
            params.append(category)
        if account:
            query += " AND account = %s"
            params.append(account)
        if is_overdue is not None:
            query += " AND (overdue_count > 0) = %s"
            params.append(is_overdue)
        if not include_paid:
            # Settled one-offs drop off the landing page; series stay while active.
            query += " AND (kind = 'series' OR unpaid_count > 0)"
        query += " ORDER BY (overdue_count > 0) DESC, next_due_date ASC NULLS LAST, name ASC"
        return paginate(cursor, query, params, page, page_size)

    return run_atomic(work, user_id=user_id)
