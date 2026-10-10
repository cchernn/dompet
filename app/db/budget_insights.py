from ..utils.db import run_atomic, like_pattern


def _budget_filter(q: str = None) -> tuple[str, list]:
    where = "WHERE 1=1"
    params = []
    if q:
        where += " AND b.name ILIKE %s"
        params.append(like_pattern(q))
    return where, params


def summarize_budgets(user_id, q: str = None) -> dict:
    where, params = _budget_filter(q)

    def work(cursor):
        cursor.execute(
            f"""
            SELECT COUNT(*) AS budget_count
            FROM dompet.vw_budgets b
            {where}
            """,
            params,
        )
        budget_count = cursor.fetchone()["budget_count"]

        cursor.execute(
            f"""
            SELECT
                COUNT(DISTINCT t.id) AS total_transactions,
                COALESCE(SUM(t.amount) FILTER (WHERE t.type = 'income'), 0) AS total_income,
                COALESCE(SUM(t.amount) FILTER (WHERE t.type = 'expenditure'), 0) AS total_expense
            FROM dompet.vw_budgets b
            JOIN dompet.transaction_budgets tb ON tb.budget_id = b.id
            JOIN dompet.transactions t ON t.id = tb.transaction_id AND t.is_active = TRUE
            {where}
            """,
            params,
        )
        totals = cursor.fetchone()

        cursor.execute(
            f"""
            SELECT b.name AS budget, SUM(t.amount) AS total, COUNT(t.id) AS count
            FROM dompet.vw_budgets b
            JOIN dompet.transaction_budgets tb ON tb.budget_id = b.id
            JOIN dompet.transactions t ON t.id = tb.transaction_id AND t.is_active = TRUE
            {where}
            GROUP BY b.name
            ORDER BY total DESC
            """,
            params,
        )
        by_budget = cursor.fetchall()

        return {
            "budget_count": budget_count,
            "total_transactions": totals["total_transactions"],
            "total_income": totals["total_income"],
            "total_expense": totals["total_expense"],
            "net": totals["total_income"] - totals["total_expense"],
            "by_budget": by_budget,
        }

    return run_atomic(work, user_id=user_id)


def trend_budgets(user_id, bucket: str, date_from: str = None, date_to: str = None, q: str = None) -> list[dict]:
    where, params = _budget_filter(q)
    if date_from:
        where += " AND t.datetime::date >= %s"
        params.append(date_from)
    if date_to:
        where += " AND t.datetime::date <= %s"
        params.append(date_to)

    def work(cursor):
        cursor.execute(
            f"""
            SELECT
                date_trunc(%s, t.datetime) AS period_start,
                COALESCE(SUM(t.amount) FILTER (WHERE t.type = 'income'), 0) AS income,
                COALESCE(SUM(t.amount) FILTER (WHERE t.type = 'expenditure'), 0) AS expense,
                COUNT(DISTINCT t.id) AS count
            FROM dompet.vw_budgets b
            JOIN dompet.transaction_budgets tb ON tb.budget_id = b.id
            JOIN dompet.transactions t ON t.id = tb.transaction_id AND t.is_active = TRUE
            {where}
            GROUP BY period_start
            ORDER BY period_start
            """,
            [bucket, *params],
        )
        return cursor.fetchall()

    return run_atomic(work, user_id=user_id)
