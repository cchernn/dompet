from ..utils.db import run_atomic
from ..utils.transaction_filter import build_transaction_filter

UNCATEGORIZED = "Uncategorized"

# Breakdowns (category/account/budget/user) describe money actually spent or
# earned, so transfers between your own accounts are left out of them; the
# per-currency totals report transfers separately instead.
_NON_TRANSFER = "type <> 'transfer'"

_SUMS = """
    COALESCE(SUM(amount) FILTER (WHERE type = 'income'), 0) AS total_income,
    COALESCE(SUM(amount) FILTER (WHERE type = 'expenditure'), 0) AS total_expense,
    COUNT(*) AS count
"""


def _order_currencies(currencies, default_currency, counts: dict) -> list[str]:
    """The user's default currency first, the rest by activity (then code)."""
    return sorted(
        currencies,
        key=lambda c: (c != default_currency, -counts.get(c, 0), c),
    )


def summarize_transactions(user_id, q: dict) -> dict:
    where, params = build_transaction_filter(q)

    def work(cursor):
        cursor.execute("SELECT default_currency FROM dompet.users WHERE id = %s", (str(user_id),))
        profile = cursor.fetchone()
        default_currency = profile["default_currency"] if profile else None

        cursor.execute(
            f"""
            SELECT
                currency,
                COALESCE(SUM(amount) FILTER (WHERE type = 'income'), 0) AS total_income,
                COALESCE(SUM(amount) FILTER (WHERE type = 'expenditure'), 0) AS total_expense,
                COALESCE(SUM(amount) FILTER (WHERE type = 'transfer'), 0) AS total_transfer,
                COUNT(*) AS transaction_count
            FROM dompet.vw_transactions
            {where}
            GROUP BY currency
            """,
            params,
        )
        totals = cursor.fetchall()

        cursor.execute(
            f"""
            SELECT currency, COALESCE(category, '{UNCATEGORIZED}') AS category, {_SUMS}
            FROM dompet.vw_transactions
            {where} AND {_NON_TRANSFER}
            GROUP BY currency, COALESCE(category, '{UNCATEGORIZED}')
            """,
            params,
        )
        by_category = cursor.fetchall()

        # A transaction counts toward both its source and its destination
        # account (once, if they are the same), so the rows overlap by design.
        cursor.execute(
            f"""
            SELECT currency, account, {_SUMS}
            FROM dompet.vw_transactions
            CROSS JOIN LATERAL (
                SELECT DISTINCT a AS account FROM unnest(ARRAY[source, destination]) AS a WHERE a IS NOT NULL
            ) accounts
            {where} AND {_NON_TRANSFER}
            GROUP BY currency, account
            """,
            params,
        )
        by_account = cursor.fetchall()

        cursor.execute(
            f"""
            SELECT currency, budget, {_SUMS}
            FROM dompet.vw_transactions, unnest(budgets) AS budget
            {where} AND {_NON_TRANSFER}
            GROUP BY currency, budget
            """,
            params,
        )
        by_budget = cursor.fetchall()

        cursor.execute(
            f"""
            SELECT currency, user_id, username, display_name, {_SUMS}
            FROM dompet.vw_transactions
            {where} AND {_NON_TRANSFER}
            GROUP BY currency, user_id, username, display_name
            """,
            params,
        )
        by_user = cursor.fetchall()

        counts = {row["currency"]: row["transaction_count"] for row in totals}
        currencies = _order_currencies(counts, default_currency, counts)
        rank = {c: i for i, c in enumerate(currencies)}

        def ordered(rows):
            rows = [{**row, "net": row["total_income"] - row["total_expense"]} for row in rows]
            return sorted(rows, key=lambda r: (rank[r["currency"]], -r["total_expense"], -r["total_income"]))

        by_total = {
            t["currency"]: {
                "total_income": t["total_income"],
                "total_expense": t["total_expense"],
                "total_transfer": t["total_transfer"],
                "net": t["total_income"] - t["total_expense"],
                "transaction_count": t["transaction_count"],
            }
            for t in sorted(totals, key=lambda t: rank[t["currency"]])
        }

        return {
            "default_currency": default_currency,
            "currencies": currencies,
            "by_total": by_total,
            "by_category": ordered(by_category),
            "by_account": ordered(by_account),
            "by_budget": ordered(by_budget),
            "by_user": ordered(by_user),
        }

    return run_atomic(work, user_id=user_id)


def trend_transactions(user_id, bucket: str, q: dict) -> dict:
    where, params = build_transaction_filter(q)

    def work(cursor):
        cursor.execute("SELECT default_currency FROM dompet.users WHERE id = %s", (str(user_id),))
        profile = cursor.fetchone()
        default_currency = profile["default_currency"] if profile else None

        # Buckets are cut in UTC (the session timezone); `count` includes
        # transfers, income/expense do not.
        cursor.execute(
            f"""
            SELECT
                date_trunc(%s, datetime) AS period_start,
                currency,
                COALESCE(SUM(amount) FILTER (WHERE type = 'income'), 0) AS income,
                COALESCE(SUM(amount) FILTER (WHERE type = 'expenditure'), 0) AS expense,
                COUNT(*) AS count
            FROM dompet.vw_transactions
            {where}
            GROUP BY period_start, currency
            ORDER BY period_start, currency
            """,
            [bucket, *params],
        )
        rows = cursor.fetchall()

        counts = {}
        for row in rows:
            counts[row["currency"]] = counts.get(row["currency"], 0) + row["count"]
        currencies = _order_currencies(counts, default_currency, counts)
        rank = {c: i for i, c in enumerate(currencies)}
        rows = sorted(rows, key=lambda r: (r["period_start"], rank[r["currency"]]))
        return {"default_currency": default_currency, "currencies": currencies, "rows": rows}

    return run_atomic(work, user_id=user_id)
