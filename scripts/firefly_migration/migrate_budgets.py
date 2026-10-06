"""One-off migration of Firefly III's Budget module into Dompet v2 budgets.

Standalone from migrate.py on purpose -- see the docstring in
scripts/legacy_dompet_migration/migrate_budgets.py for why (Phase 4 already
executed; create_transaction is not idempotent). This script only touches
dompet.budgets/budget_members/transaction_budgets, resolving already-migrated
transactions via operations.metadata->>'source_id'.

Only the historical budget_transaction_journal links are migrated (plain
data -- these are just the already-decided output of Firefly's Rules
engine). The Rules engine itself (multi-condition triggers, set_budget/
link_to_bill actions), budget_limits (spending caps), and auto_budgets
(auto-renewing caps) are explicitly out of scope for this pass -- deferred
alongside the Bills/subscriptions feature.

Cross-source merging (e.g. this budget's "Allevia" == legacy's "Allevia Mont
Kiara" group) happens via scripts.budget_aliases.canonical_name plus
app.db.budget.create_budget's own case-insensitive get-or-create -- shared
with scripts/legacy_dompet_migration/migrate_budgets.py so run order never
matters.

Usage:
    python3 -m scripts.firefly_migration.migrate_budgets <dump_path> <cognito_user_id> [--execute]
"""

import argparse

from psycopg2.extras import RealDictCursor

from app.utils.env import load_local_env
from app.utils.db import connect
from app.db import budget as budget_db
from app.db import transaction_budget as transaction_budget_db

from .parse_dump import parse_dump
from ..budget_aliases import canonical_name


def build_transaction_id_map(cursor, user_id: str) -> dict:
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
    parser = argparse.ArgumentParser(description="Migrate Firefly III budgets into Dompet v2")
    parser.add_argument("dump_path")
    parser.add_argument("user_id", help="Cognito UUID that owns the migrated budgets")
    parser.add_argument("--execute", action="store_true", help="Actually write to the database (default: dry run)")
    args = parser.parse_args()

    tables = parse_dump(args.dump_path)
    active_budgets = [b for b in tables["budgets"] if b["deleted_at"] is None]

    links_by_budget = {}
    for link in tables["budget_transaction_journal"]:
        links_by_budget.setdefault(link["budget_id"], []).append(link["transaction_journal_id"])

    load_local_env()
    conn = connect()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            txn_id_map = build_transaction_id_map(cursor, args.user_id)
        conn.rollback()  # read-only connection; all writes happen via run_atomic in the db.* calls below
    finally:
        conn.close()

    warnings = []
    links_created = 0

    for b in active_budgets:
        name = canonical_name(b["name"])
        if args.execute:
            budget_id = budget_db.create_budget(args.user_id, {"name": name})["id"]

        for journal_id in links_by_budget.get(b["id"], []):
            dompet_txn_id = txn_id_map.get(journal_id)
            if not dompet_txn_id:
                warnings.append(f"budget {b['id']} ({b['name']}): journal {journal_id} was never migrated, skipped")
                continue
            if args.execute:
                transaction_budget_db.link_budget(args.user_id, dompet_txn_id, budget_id)
            links_created += 1

    print(f"=== {'EXECUTE' if args.execute else 'DRY RUN'} ===")
    print(f"budgets to migrate:  {len(active_budgets)}")
    print(f"links created:       {links_created}")
    print(f"warnings:            {len(warnings)}")
    if warnings:
        print("\n=== warnings ===")
        for w in warnings:
            print(" ", w)


if __name__ == "__main__":
    main()
