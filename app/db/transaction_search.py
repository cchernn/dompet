from ..utils.db import run_atomic, paginate


def search_transactions(
    user_id, page: int, page_size: int,
    date_from: str = None, date_to: str = None,
    category: str = None, transaction_type: str = None,
    source: str = None, destination: str = None,
    tags: str = None, budgets: str = None,
    source_location: str = None, destination_location: str = None,
    owner: str = None,
) -> tuple[list[dict], dict]:
    def work(cursor):
        query = "SELECT * FROM dompet.vw_transactions WHERE 1=1"
        params = []
        if date_from:
            query += " AND date >= %s"
            params.append(date_from)
        if date_to:
            query += " AND date <= %s"
            params.append(date_to)
        if category:
            query += " AND category = %s"
            params.append(category)
        if transaction_type:
            query += " AND type = %s"
            params.append(transaction_type)
        if source:
            query += " AND source = %s"
            params.append(source)
        if destination:
            query += " AND destination = %s"
            params.append(destination)
        if tags:
            query += " AND %s = ANY(tags)"
            params.append(tags)
        if budgets:
            query += " AND %s = ANY(budgets)"
            params.append(budgets)
        if source_location:
            query += " AND source_location = %s"
            params.append(source_location)
        if destination_location:
            query += " AND destination_location = %s"
            params.append(destination_location)
        if owner:
            query += " AND user_id = %s"
            params.append(owner)
        query += " ORDER BY datetime DESC"
        return paginate(cursor, query, params, page, page_size)

    return run_atomic(work, user_id=user_id)
