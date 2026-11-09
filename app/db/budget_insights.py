from ..utils.db import run_atomic, like_pattern


def _budget_filter(q: str = None) -> tuple[str, list]:
    where = "WHERE 1=1"
    params = []
    if q:
        where += " AND b.name ILIKE %s"
        params.append(like_pattern(q))
    return where, params


def _date_filter(date_from: str = None, date_to: str = None) -> tuple[str, list]:
    where = ""
    params = []
    if date_from:
        where += " AND t.datetime::date >= %s"
        params.append(date_from)
    if date_to:
        where += " AND t.datetime::date <= %s"
        params.append(date_to)
    return where, params


def summarize_budgets(user_id, q: str = None, date_from: str = None, date_to: str = None) -> dict:
    base_where, base_params = _budget_filter(q)
    date_where, date_params = _date_filter(date_from, date_to)
    where = base_where + date_where
    params = base_params + date_params

    def work(cursor):
        # LEFT JOIN here (unlike the two queries below) so a budget with no
        # transactions still counts when there's no date filter -- adding a
        # date condition on t.datetime then effectively narrows this to
        # "budgets with activity in range", which is the intended behavior.
        cursor.execute(
            f"""
            SELECT COUNT(DISTINCT b.id) AS budget_count
            FROM dompet.vw_budgets b
            LEFT JOIN dompet.transaction_budgets tb ON tb.budget_id = b.id
            LEFT JOIN dompet.transactions t ON t.id = tb.transaction_id AND t.is_active = TRUE
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
    base_where, base_params = _budget_filter(q)
    date_where, date_params = _date_filter(date_from, date_to)
    where = base_where + date_where
    params = base_params + date_params

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
