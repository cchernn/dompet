from ..utils.db import run_atomic


def _build_filter(q: dict) -> tuple[str, list]:
    """Same filter set as transaction_search.search_transactions, minus
    pagination/ordering and the owner filter (not part of the insights
    spec) -- names, not ids, since this reads from vw_transactions same
    as search does."""
    where = "WHERE 1=1"
    params = []
    if q.get("from"):
        where += " AND date >= %s"
        params.append(q["from"])
    if q.get("to"):
        where += " AND date <= %s"
        params.append(q["to"])
    if q.get("category"):
        where += " AND category = %s"
        params.append(q["category"])
    if q.get("type"):
        where += " AND type = %s"
        params.append(q["type"])
    if q.get("source"):
        where += " AND source = %s"
        params.append(q["source"])
    if q.get("destination"):
        where += " AND destination = %s"
        params.append(q["destination"])
    if q.get("tags"):
        where += " AND %s = ANY(tags)"
        params.append(q["tags"])
    if q.get("budgets"):
        where += " AND %s = ANY(budgets)"
        params.append(q["budgets"])
    return where, params


def summarize_transactions(user_id, q: dict) -> dict:
    where, params = _build_filter(q)

    def work(cursor):
        cursor.execute(
            f"""
            SELECT
                COALESCE(SUM(amount) FILTER (WHERE type = 'income'), 0) AS total_income,
                COALESCE(SUM(amount) FILTER (WHERE type = 'expenditure'), 0) AS total_expense,
                COUNT(*) AS transaction_count
            FROM dompet.vw_transactions
            {where}
            """,
            params,
        )
        totals = cursor.fetchone()

        cursor.execute(
            f"""
            SELECT category, SUM(amount) AS total, COUNT(*) AS count
            FROM dompet.vw_transactions
            {where} AND category IS NOT NULL
            GROUP BY category
            ORDER BY total DESC
            """,
            params,
        )
        by_category = cursor.fetchall()

        cursor.execute(
            f"""
            SELECT source AS account, SUM(amount) AS total, COUNT(*) AS count
            FROM dompet.vw_transactions
            {where} AND source IS NOT NULL
            GROUP BY source
            ORDER BY total DESC
            """,
            params,
        )
        by_account = cursor.fetchall()

        cursor.execute(
            f"""
            SELECT destination AS account, SUM(amount) AS total, COUNT(*) AS count
            FROM dompet.vw_transactions
            {where} AND destination IS NOT NULL
            GROUP BY destination
            ORDER BY total DESC
            """,
            params,
        )
        by_destination_account = cursor.fetchall()

        cursor.execute(
            f"""
            SELECT budget, SUM(amount) AS total, COUNT(*) AS count
            FROM dompet.vw_transactions, unnest(budgets) AS budget
            {where}
            GROUP BY budget
            ORDER BY total DESC
            """,
            params,
        )
        by_budget = cursor.fetchall()

        return {
            "total_income": totals["total_income"],
            "total_expense": totals["total_expense"],
            "net": totals["total_income"] - totals["total_expense"],
            "transaction_count": totals["transaction_count"],
            "by_category": by_category,
            "by_account": by_account,
            "by_destination_account": by_destination_account,
            "by_budget": by_budget,
        }

    return run_atomic(work, user_id=user_id)


def trend_transactions(user_id, bucket: str, q: dict) -> list[dict]:
    where, params = _build_filter(q)

    def work(cursor):
        cursor.execute(
            f"""
            SELECT
                date_trunc(%s, datetime) AS period_start,
                COALESCE(SUM(amount) FILTER (WHERE type = 'income'), 0) AS income,
                COALESCE(SUM(amount) FILTER (WHERE type = 'expenditure'), 0) AS expense,
                COUNT(*) AS count
            FROM dompet.vw_transactions
            {where}
            GROUP BY period_start
            ORDER BY period_start
            """,
            [bucket, *params],
        )
        return cursor.fetchall()

    return run_atomic(work, user_id=user_id)
