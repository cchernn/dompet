"""One-off correction: the earlier datetime backfill
(backfill_transaction_datetime.py) stored Firefly's real timestamps
verbatim into a TIMESTAMPTZ column, which Postgres then labeled as UTC --
but Firefly's wall-clock values are actually Asia/Kuala_Lumpur (MYT),
confirmed by cross-checking meal-time transactions (breakfast/lunch/dinner
only make sense in MYT, not UTC -- e.g. "dinner" at the stored value would
be 1-4am if it were really UTC).

Corrects exactly the rows that backfill touched, identified via its own
audit trail (dompet.operations.metadata->>'source' =
'firefly_datetime_backfill'), reinterpreting each stored wall-clock value
as MYT and storing the correct UTC instant instead. Deliberately does NOT
touch the rows that were already midnight (never modified by that
backfill) -- there's no way to know if midnight was ever a real recorded
time or just a "no time known" default, and shifting it risks moving the
date to the wrong day for no informational gain.

Usage:
    python3 -m scripts.fix_transaction_timezone <cognito_user_id> [--execute]
"""

import argparse

from psycopg2.extras import RealDictCursor

from app.utils.env import load_local_env
from app.utils.db import connect
from app.db import transaction_operation


def find_corrections(cursor, user_id: str) -> list:
    cursor.execute(
        """
        SELECT t.id, t.datetime,
               (t.datetime AT TIME ZONE 'UTC') AT TIME ZONE 'Asia/Kuala_Lumpur' AS corrected
        FROM dompet.transactions t
        WHERE t.user_id = %s
          AND t.id IN (
              SELECT DISTINCT entity_id FROM dompet.operations
              WHERE entity_type = 'transaction' AND operation_type = 'UPDATE'
                    AND metadata->>'source' = 'firefly_datetime_backfill' AND user_id = %s
          )
        """,
        (str(user_id), str(user_id)),
    )
    return cursor.fetchall()


def main():
    parser = argparse.ArgumentParser(description="Fix timezone on Firefly-sourced transaction timestamps")
    parser.add_argument("user_id", help="Cognito UUID that owns the transactions")
    parser.add_argument("--execute", action="store_true", help="Actually write to the database (default: dry run)")
    args = parser.parse_args()

    load_local_env()
    conn = connect()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            rows = find_corrections(cursor, args.user_id)
        conn.rollback()
    finally:
        conn.close()

    print(f"=== {'EXECUTE' if args.execute else 'DRY RUN'} ===")
    print(f"transactions to correct: {len(rows)}")
    for row in rows[:5]:
        print(f"  sample: {row['datetime']} -> {row['corrected']}")

    if args.execute:
        for i, row in enumerate(rows, 1):
            transaction_operation.update_transaction(
                args.user_id, row["id"], {"datetime": row["corrected"].isoformat()},
                metadata={
                    "source": "firefly_timezone_fix",
                    "reason": "reinterpret Firefly wall-clock time as Asia/Kuala_Lumpur, not UTC",
                },
            )
            if i % 200 == 0:
                print(f"{i}/{len(rows)} corrected")
        print(f"done: {len(rows)} corrected")


if __name__ == "__main__":
    main()
