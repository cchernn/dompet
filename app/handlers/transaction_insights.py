from ..lib.params import Params
from ..models.transaction_insights import TransactionSummary, TransactionTrend, TransactionTrendPoint
from ..db import transaction_insights as transaction_insights_db
from ..utils.trend import parse_bucket, bucket_label


def summary(params: Params) -> TransactionSummary:
    q = params.queryParams or {}
    result = transaction_insights_db.summarize_transactions(params.user, q)
    return TransactionSummary(**result)


def trend(params: Params) -> TransactionTrend:
    q = params.queryParams or {}
    bucket = parse_bucket(q.get("bucket"))
    result = transaction_insights_db.trend_transactions(params.user, bucket, q)
    series = [
        TransactionTrendPoint(
            period_start=row["period_start"],
            period_label=bucket_label(bucket, row["period_start"]),
            currency=row["currency"],
            income=row["income"],
            expense=row["expense"],
            net=row["income"] - row["expense"],
            count=row["count"],
        )
        for row in result["rows"]
    ]
    return TransactionTrend(
        default_currency=result["default_currency"],
        currencies=result["currencies"],
        bucket=bucket,
        series=series,
    )
