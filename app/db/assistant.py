import json

from ..utils.db import run_atomic

RATE_LIMIT_WINDOW_MINUTES = 10
RATE_LIMIT_MAX_QUERIES = 20


def count_recent_queries(user_id, window_minutes: int = RATE_LIMIT_WINDOW_MINUTES) -> int:
    def work(cursor):
        cursor.execute(
            """
            SELECT COUNT(*) AS count FROM dompet.assistant_queries
            WHERE user_id = %s AND created_at > NOW() - (%s * INTERVAL '1 minute')
            """,
            (str(user_id), window_minutes),
        )
        return cursor.fetchone()["count"]

    return run_atomic(work, user_id=user_id)


def log_query(
    user_id, message_length: int, round_count: int, tool_calls: list,
    stop_reason: str = None, error_type: str = None, latency_ms: int = 0,
) -> None:
    def work(cursor):
        cursor.execute(
            """
            INSERT INTO dompet.assistant_queries
                (user_id, message_length, round_count, tool_calls, stop_reason, error_type, latency_ms)
            VALUES (%s, %s, %s, %s::jsonb, %s, %s, %s)
            """,
            (str(user_id), message_length, round_count, json.dumps(tool_calls), stop_reason, error_type, latency_ms),
        )

    run_atomic(work, user_id=user_id)
