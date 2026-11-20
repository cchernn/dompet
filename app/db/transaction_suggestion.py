from datetime import datetime, timedelta, timezone

from ..lib.exceptions import InvalidDataException
from ..utils.db import run_atomic, paginate, like_pattern
from .transaction_operation import TRANSACTION_TYPES

# Only the strongest candidates get the time-of-day boost, which re-scans
# each one's history -- plenty, since a page only ever shows a handful.
MAX_CANDIDATES = 100
DEFAULT_MIN_USES = 2

# A past use "matches the time" when it falls within this many hours of now
# (wrapping around midnight) on the same kind of day (weekday vs weekend).
TIME_WINDOW_HOURS = 2


def _parse_int(name: str, value, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise InvalidDataException(ValueError(f"{name} must be an integer: {value}"))
    if not minimum <= parsed <= maximum:
        raise InvalidDataException(ValueError(f"{name} must be between {minimum} and {maximum}"))
    return parsed


def search_suggestions(
    user_id, page: int, page_size: int,
    q: str = None, transaction_type: str = None, min_uses=None, tz_offset=None,
) -> tuple[list[dict], dict]:
    """Ranked suggestions for the caller. `tz_offset` is the caller's UTC
    offset in minutes east of UTC (480 for Malaysia); when given, patterns
    the caller usually records around this time of day, on this kind of day,
    are boosted up to 2x. Without it, ranking is recency-weighted frequency
    alone."""
    if transaction_type and transaction_type not in TRANSACTION_TYPES:
        raise InvalidDataException(ValueError(f"Invalid transaction type: {transaction_type}"))
    min_uses = DEFAULT_MIN_USES if min_uses in (None, "") else _parse_int("min_uses", min_uses, 1, 1000)
    if tz_offset in (None, ""):
        tz_offset = None
    else:
        tz_offset = _parse_int("tz_offset", tz_offset, -840, 840)

    def work(cursor):
        where = "user_id = %s AND times_used >= %s"
        params = [str(user_id), min_uses]
        if q:
            where += " AND name ILIKE %s"
            params.append(like_pattern(q))
        if transaction_type:
            where += " AND type = %s"
            params.append(transaction_type)

        candidates = f"""
            SELECT * FROM dompet.vw_transaction_suggestions
            WHERE {where}
            ORDER BY score DESC, last_used DESC
            LIMIT {MAX_CANDIDATES}
        """

        if tz_offset is None:
            query = f"""
                WITH cand AS ({candidates})
                SELECT cand.*, 0 AS time_matches, cand.score AS ranked_score
                FROM cand
                ORDER BY ranked_score DESC, last_used DESC
            """
            query_params = params
        else:
            local_now = datetime.now(timezone.utc) + timedelta(minutes=tz_offset)
            query = f"""
                WITH cand AS ({candidates}),
                ranked AS (
                    SELECT cand.*,
                           COALESCE(m.time_matches, 0) AS time_matches,
                           cand.score * (1 + COALESCE(m.time_matches, 0)::float8 / cand.times_used) AS ranked_score
                    FROM cand
                    LEFT JOIN LATERAL (
                        SELECT COUNT(*) AS time_matches
                        FROM dompet.transactions t
                        CROSS JOIN LATERAL (
                            SELECT t.datetime + make_interval(mins => %s) AS local_dt
                        ) l
                        WHERE t.user_id = cand.user_id AND t.is_active
                          AND t.name = cand.name AND t.type = cand.type
                          AND t.currency_code = cand.currency
                          AND t.source_account_id = cand.source_account_id
                          AND t.destination_account_id = cand.destination_account_id
                          AND t.category_id IS NOT DISTINCT FROM cand.category_id
                          AND LEAST(
                                ABS(EXTRACT(HOUR FROM l.local_dt)::int - %s),
                                24 - ABS(EXTRACT(HOUR FROM l.local_dt)::int - %s)
                              ) <= {TIME_WINDOW_HOURS}
                          AND (EXTRACT(ISODOW FROM l.local_dt) >= 6) = %s
                    ) m ON TRUE
                )
                SELECT * FROM ranked
                ORDER BY ranked_score DESC, last_used DESC
            """
            query_params = params + [tz_offset, local_now.hour, local_now.hour, local_now.isoweekday() >= 6]

        return paginate(cursor, query, query_params, page, page_size)

    return run_atomic(work, user_id=user_id)
