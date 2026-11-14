from ..utils.db import run_atomic, paginate, like_pattern
from .statement import sync_statements


def search_statements(
    user_id, page: int, page_size: int,
    q: str = None, account: str = None, account_id: str = None,
    is_recurring: bool = None, status: str = None,
    date_from: str = None, date_to: str = None,
) -> tuple[list[dict], dict]:
    def work(cursor):
        sync_statements(cursor, user_id)

        query = "SELECT * FROM dompet.vw_statements WHERE 1=1"
        params = []
        if q:
            query += " AND (account ILIKE %s OR notes ILIKE %s)"
            params.extend([like_pattern(q), like_pattern(q)])
        if account:
            query += " AND account = %s"
            params.append(account)
        if account_id:
            query += " AND account_id = %s"
            params.append(account_id)
        if is_recurring is not None:
            query += " AND is_recurring = %s"
            params.append(is_recurring)
        if status:
            query += " AND status = %s"
            params.append(status)
        if date_from:
            query += " AND statement_date >= %s"
            params.append(date_from)
        if date_to:
            query += " AND statement_date <= %s"
            params.append(date_to)
        query += " ORDER BY statement_date DESC, account ASC"
        return paginate(cursor, query, params, page, page_size)

    return run_atomic(work, user_id=user_id)
