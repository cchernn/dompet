from ..utils.db import run_atomic, paginate, like_pattern
from .bill import sync_bills


def search_bills(
    user_id, page: int, page_size: int,
    q: str = None, category: str = None, account: str = None,
    is_recurring: bool = None, status: str = None,
    date_from: str = None, date_to: str = None,
) -> tuple[list[dict], dict]:
    def work(cursor):
        sync_bills(cursor, user_id)

        query = "SELECT * FROM dompet.vw_bills WHERE 1=1"
        params = []
        if q:
            query += " AND name ILIKE %s"
            params.append(like_pattern(q))
        if category:
            query += " AND category = %s"
            params.append(category)
        if account:
            query += " AND account = %s"
            params.append(account)
        if is_recurring is not None:
            query += " AND is_recurring = %s"
            params.append(is_recurring)
        if status:
            query += " AND status = %s"
            params.append(status)
        if date_from:
            query += " AND due_date >= %s"
            params.append(date_from)
        if date_to:
            query += " AND due_date <= %s"
            params.append(date_to)
        query += " ORDER BY due_date ASC"
        return paginate(cursor, query, params, page, page_size)

    return run_atomic(work, user_id=user_id)
