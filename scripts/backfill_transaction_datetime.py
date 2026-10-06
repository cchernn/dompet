"""Backfills real hour:minute timestamps for Firefly-sourced transactions.

scripts/firefly_migration/migrate.py::build_transaction() has always
truncated Firefly's real journal timestamp to just the date
(journal["date"][:10]) before storing, even after the datetime column was
introduced (migration 022) -- every Firefly-sourced transaction, from the
original Phase 4 import through the later 72-row delta, ended up at
midnight instead of its real time. That's now fixed going forward (see
migrate.py), but the already-migrated rows still need correcting.

Resolves each transaction's Firefly journal id via
dompet.operations.metadata->>'source_id' (same established pattern as
migrate_delta.py/migrate_attachments.py), then updates datetime through
app.db.transaction_operation.update_transaction -- same as any other edit,
so it goes through the normal validation and leaves a proper "UPDATE"
audit trail entry. Safe to re-run: skips any row whose datetime already
matches the dump's value.

Usage:
    python3 -m scripts.backfill_transaction_datetime <dump_path> <cognito_user_id> [--execute]
"""

import argparse

from psycopg2.extras import RealDictCursor

from app.utils.env import load_local_env
from app.utils.db import connect
from app.db import transaction_operation

from .firefly_migration.parse_dump import parse_dump


def build_journal_datetime_map(tables: dict) -> dict:
    return {
        j["id"]: j["date"]
        for j in tables["transaction_journals"]
        if j["deleted_at"] is None
    }


def build_migrated_journal_map(cursor, user_id: str) -> dict:
    cursor.execute(
        """
        SELECT entity_id AS transaction_id, metadata->>'source_id' AS source_id
        FROM dompet.operations
        WHERE entity_type = 'transaction' AND operation_type = 'CREATE'
              AND metadata->>'source' = 'firefly' AND user_id = %s
        """,
        (str(user_id),),
    )
    return {row["source_id"]: row["transaction_id"] for row in cursor.fetchall()}


def main():
    parser = argparse.ArgumentParser(description="Backfill real timestamps for Firefly-sourced transactions")
    parser.add_argument("dump_path")
    parser.add_argument("user_id", help="Cognito UUID that owns the Firefly-sourced transactions")
    parser.add_argument("--execute", action="store_true", help="Actually write to the database (default: dry run)")
    args = parser.parse_args()

    tables = parse_dump(args.dump_path)
    journal_datetimes = build_journal_datetime_map(tables)

    load_local_env()
    conn = connect()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            journal_to_txn = build_migrated_journal_map(cursor, args.user_id)
            txn_ids = [str(v) for v in journal_to_txn.values()]
            cursor.execute(
                "SELECT id, datetime FROM dompet.transactions WHERE id = ANY(%s::uuid[])",
                (txn_ids,),
            )
            current_datetimes = {str(row["id"]): row["datetime"] for row in cursor.fetchall()}
        conn.rollback()  # read-only connection; all writes happen via run_atomic in transaction_operation.update_transaction
    finally:
        conn.close()

    updated = 0
    unchanged = 0
    missing_in_dump = 0

    for source_id, txn_id in journal_to_txn.items():
        real_datetime = journal_datetimes.get(source_id)
        if not real_datetime:
            missing_in_dump += 1
            continue

        current = current_datetimes.get(str(txn_id))
        if current is not None and current.strftime("%Y-%m-%d %H:%M:%S") == real_datetime:
            unchanged += 1
            continue

        if args.execute:
            transaction_operation.update_transaction(
                args.user_id, txn_id, {"datetime": real_datetime},
                metadata={"source": "firefly_datetime_backfill"},
            )
        updated += 1

    print(f"=== {'EXECUTE' if args.execute else 'DRY RUN'} ===")
    print(f"firefly transactions mapped: {len(journal_to_txn)}")
    print(f"updated:                     {updated}")
    print(f"already correct:             {unchanged}")
    print(f"missing in dump:             {missing_in_dump}")


if __name__ == "__main__":
    main()
