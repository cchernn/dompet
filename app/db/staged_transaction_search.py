from ..utils.db import run_atomic, paginate, like_pattern


def search_staged(
    user_id, page: int, page_size: int,
    q: str = None, status: str = "draft", transaction_type: str = None, origin: str = None,
    is_complete: bool = None, account_id: str = None,
) -> tuple[list[dict], dict]:
    def work(cursor):
        query = "SELECT * FROM dompet.vw_staged_transactions WHERE 1=1"
        params = []
        if status and status != "all":
            query += " AND status = %s"
            params.append(status)
        if q:
            query += " AND (name ILIKE %s OR notes ILIKE %s)"
            params.extend([like_pattern(q), like_pattern(q)])
        if transaction_type:
            query += " AND type = %s"
            params.append(transaction_type)
        if origin:
            query += " AND origin = %s"
            params.append(origin)
        if is_complete is not None:
            query += " AND is_complete = %s"
            params.append(is_complete)
        if account_id:
            query += " AND (source_account_id = %s OR destination_account_id = %s)"
            params.extend([account_id, account_id])
        query += " ORDER BY created_at DESC"
        return paginate(cursor, query, params, page, page_size)

    return run_atomic(work, user_id=user_id)
