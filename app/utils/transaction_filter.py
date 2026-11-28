from .db import like_pattern
from .filters import parse_owner_filter


def build_transaction_filter(q: dict) -> tuple[str, list]:
    """The one WHERE clause over dompet.vw_transactions shared by
    /transactions/search, /transactions/summary and /transactions/trend, so
    the same query string always selects the same rows in all three (names,
    not ids, since the view exposes names). `account` matches a transaction
    on either side: source or destination."""
    where = "WHERE 1=1"
    params = []
    if q.get("q"):
        where += " AND name ILIKE %s"
        params.append(like_pattern(q["q"]))
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
    if q.get("account"):
        where += " AND (source = %s OR destination = %s)"
        params.extend([q["account"], q["account"]])
    if q.get("tags"):
        where += " AND %s = ANY(tags)"
        params.append(q["tags"])
    if q.get("budgets"):
        where += " AND %s = ANY(budgets)"
        params.append(q["budgets"])
    if q.get("source_location"):
        where += " AND source_location = %s"
        params.append(q["source_location"])
    if q.get("destination_location"):
        where += " AND destination_location = %s"
        params.append(q["destination_location"])
    owner = parse_owner_filter(q.get("user_id"), allow_null=False)
    if owner:
        where += " AND user_id = %s"
        params.append(owner)
    return where, params
