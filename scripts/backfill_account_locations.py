"""One-off backfill of dompet.account_locations from already-migrated data.

Phase 5's legacy_dompet migration (scripts/legacy_dompet_migration/migrate.py)
resolves an expenditure's destination account by creating/finding an account
named after its public.locations-derived location name (see
build_public_transaction's "Migrated from a legacy Dompet location" case).
That leaves an exact, derivable relationship behind: any dompet.accounts row
with that description names a real dompet.locations row, case-insensitively,
1:1 (verified: 492/492 match, 0 unmatched). Neither legacy_expenditure
(location is folded into the transaction name as plain text, never an
account) nor Firefly (no location concept at all) produced anything
equivalent, so this backfill is scoped to legacy_dompet-sourced accounts only.

Without --execute this is a pure dry run: prints the candidate pairs, writes
nothing.

Usage:
    python3 -m scripts.backfill_account_locations [--execute]
"""

import argparse

from psycopg2.extras import RealDictCursor

from app.utils.env import load_local_env
from app.utils.db import connect
from app.db import account_location as account_location_db

SOURCE_DESCRIPTION = "Migrated from a legacy Dompet location"


def find_candidates(cursor) -> list[dict]:
    cursor.execute(
        """
        SELECT a.id AS account_id, a.user_id, a.name AS account_name, l.id AS location_id
        FROM dompet.accounts a
        JOIN dompet.locations l ON LOWER(l.name) = LOWER(a.name)
        WHERE a.description = %s
        ORDER BY a.name
        """,
        (SOURCE_DESCRIPTION,),
    )
    return cursor.fetchall()


def main():
    parser = argparse.ArgumentParser(description="Backfill dompet.account_locations from legacy_dompet-derived accounts")
    parser.add_argument("--execute", action="store_true", help="Actually write to the database (default: dry run)")
    args = parser.parse_args()

    load_local_env()
    conn = connect()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            candidates = find_candidates(cursor)
        conn.rollback()  # read-only connection; writes happen via account_location_db.link_location below
    finally:
        conn.close()

    print(f"=== {'EXECUTE' if args.execute else 'DRY RUN'} ===")
    print(f"candidate (account, location) pairs: {len(candidates)}")

    if args.execute:
        for c in candidates:
            account_location_db.link_location(c["user_id"], c["account_id"], c["location_id"])
        print(f"linked: {len(candidates)}")
    else:
        for c in candidates[:10]:
            print(" ", c["account_name"])
        if len(candidates) > 10:
            print(f"  ... and {len(candidates) - 10} more")


if __name__ == "__main__":
    main()
