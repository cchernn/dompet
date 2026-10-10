from ..lib.params import Params
from ..models.insights import TrendPoint
from ..models.budget_insights import BudgetSummary, BudgetTrend
from ..db import budget_insights as budget_insights_db
from ..utils.trend import parse_bucket, bucket_label


def summary(params: Params) -> BudgetSummary:
    q = params.queryParams or {}
    result = budget_insights_db.summarize_budgets(params.user, q.get("q"))
    return BudgetSummary(**result)


def trend(params: Params) -> BudgetTrend:
    q = params.queryParams or {}
    bucket = parse_bucket(q.get("bucket"))
    rows = budget_insights_db.trend_budgets(
        params.user, bucket, date_from=q.get("from"), date_to=q.get("to"), q=q.get("q"),
    )
    series = [
        TrendPoint(
            period_start=row["period_start"],
            period_label=bucket_label(bucket, row["period_start"]),
            income=row["income"],
            expense=row["expense"],
            net=row["income"] - row["expense"],
            count=row["count"],
        )
        for row in rows
    ]
    return BudgetTrend(bucket=bucket, series=series)
