from ..utils.db import run_atomic, paginate
from ..utils.transaction_filter import build_transaction_filter


def search_transactions(user_id, page: int, page_size: int, filters: dict) -> tuple[list[dict], dict]:
    """`filters` is the raw query-string dict; see build_transaction_filter
    for the accepted keys (shared with the summary and trend endpoints)."""
    where, params = build_transaction_filter(filters)

    def work(cursor):
        query = f"SELECT * FROM dompet.vw_transactions {where} ORDER BY datetime DESC"
        return paginate(cursor, query, params, page, page_size)

    return run_atomic(work, user_id=user_id)
