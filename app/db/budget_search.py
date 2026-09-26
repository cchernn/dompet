from ..utils.db import run_atomic, paginate, like_pattern


def search_budgets(user_id, page: int, page_size: int, q: str = None) -> tuple[list[dict], dict]:
    def work(cursor):
        query = "SELECT * FROM dompet.vw_budgets WHERE 1=1"
        params = []
        if q:
            query += " AND name ILIKE %s"
            params.append(like_pattern(q))
        query += " ORDER BY usage_count DESC, name ASC"
        return paginate(cursor, query, params, page, page_size)

    return run_atomic(work, user_id=user_id)
