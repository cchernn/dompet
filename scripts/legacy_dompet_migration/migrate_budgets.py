"""One-off migration of legacy "group" data into Dompet v2's budget module.

Standalone from migrate.py on purpose: Phase 5 (migrate.py) already executed
against live data, and app.db.transaction_operation.create_transaction is
not idempotent, so re-running migrate.py --execute would create duplicate
transactions. This script only touches dompet.budgets/budget_members/
transaction_budgets, resolving already-migrated transactions via the same
operations.metadata->>'source_id' traceability every other
migration script relies on.

Two legacy sources, two eras of the same "shared group of transactions"
idea:
  - public.transaction_groups (+ user_transaction_group, +
    transaction_transaction_group): newer, owner/members already Cognito
    UUIDs.
  - public.expenditure_expendituregroup (+ expenditure_expendituregroup_users):
    older Django-era predecessor, integer user ids. id=1 ("General") is a
    default/catch-all covering 80% of expenditure_expenditure rows, not a
    real place/trip/vehicle -- excluded entirely, same spirit as the
    mislabeled-income exclusion in migrate.py.

Cross-source merging (e.g. Firefly's "Allevia" budget == legacy's "Allevia
Mont Kiara" group) happens via scripts.budget_aliases.canonical_name plus
app.db.budget.create_budget's own case-insensitive get-or-create -- shared
with scripts/firefly_migration/migrate_budgets.py so run order never matters.

Usage:
    python3 -m scripts.legacy_dompet_migration.migrate_budgets <legacy_expenditure_user_id_1_cognito_uuid> [--execute]
"""

import argparse

from psycopg2.extras import RealDictCursor

from app.utils.env import load_local_env
from app.utils.db import connect
from app.db import budget as budget_db
from app.db import budget_member as budget_member_db
from app.db import transaction_budget as transaction_budget_db

from ..budget_aliases import canonical_name

# The only two real Cognito users in the whole system (see
# legacy_dompet_migration/migrate.py's own user-mapping notes). Django
# integer user id 6 (tanyenwen@gmail.com in public.user_user) is the second
# real user found throughout public.transactions; owner_id 1 is the CLI arg.
DJANGO_USER_6_COGNITO_UUID = "99ea956c-a0c1-7022-c795-1cd8f712ccc9"

EXCLUDED_EXPENDITUREGROUP_ID = 1  # "General" catch-all, not a real group


def resolve_django_user(django_id: int, cli_owner_cognito_uuid: str) -> str:
    if django_id == 1:
        return cli_owner_cognito_uuid
    if django_id == 6:
        return DJANGO_USER_6_COGNITO_UUID
    raise ValueError(f"Unknown legacy Django user id: {django_id}")


def build_transaction_id_map(cursor) -> dict:
    """Maps (source, source_id) -> {"transaction_id", "user_id"}. user_id is
    the transaction's *actual* owner, which is not necessarily the linking
    group/budget's owner (shared budgets can contain a member's own
    transactions) -- links must be performed as that owner, or
    transaction_budget_db.link_budget's ownership check rejects them."""
    cursor.execute("""
        SELECT entity_id AS transaction_id, user_id, metadata->>'source' AS source, metadata->>'source_id' AS source_id
        FROM dompet.operations
        WHERE entity_type = 'transaction' AND operation_type = 'CREATE'
          AND metadata->>'source' IN ('legacy_dompet', 'legacy_expenditure')
    """)
    return {
        (row["source"], row["source_id"]): {"transaction_id": row["transaction_id"], "user_id": row["user_id"]}
        for row in cursor.fetchall()
    }


def migrate_transaction_groups(cursor, txn_id_map: dict, execute: bool):
    cursor.execute("SELECT id, \"user\", name FROM public.transaction_groups")
    groups = cursor.fetchall()

    cursor.execute("SELECT transaction_group_id, \"user\" FROM public.user_transaction_group")
    members_by_group = {}
    for row in cursor.fetchall():
        members_by_group.setdefault(row["transaction_group_id"], []).append(row["user"])

    cursor.execute("SELECT transaction_id, transaction_group_id FROM public.transaction_transaction_group")
    links_by_group = {}
    for row in cursor.fetchall():
        links_by_group.setdefault(row["transaction_group_id"], []).append(row["transaction_id"])

    budget_map = {}
    warnings = []
    links_created = 0

    for g in groups:
        name = canonical_name(g["name"])
        if execute:
            row = budget_db.create_budget(g["user"], {"name": name})
            budget_id = row["id"]
        else:
            budget_id = f"<dry-run-budget-{g['id']}>"
        budget_map[g["id"]] = budget_id

        for member in members_by_group.get(g["id"], []):
            if member == g["user"]:
                continue
            if execute:
                budget_member_db.add_member(g["user"], budget_id, member)

        for old_txn_id in links_by_group.get(g["id"], []):
            entry = txn_id_map.get(("legacy_dompet", str(old_txn_id)))
            if not entry:
                warnings.append(f"transaction_groups {g['id']} ({g['name']}): transaction {old_txn_id} was never migrated, skipped")
                continue
            if execute:
                transaction_budget_db.link_budget(entry["user_id"], entry["transaction_id"], budget_id)
            links_created += 1

    return budget_map, warnings, links_created, len(groups)


def migrate_expenditure_groups(cursor, cli_owner_cognito_uuid: str, txn_id_map: dict, execute: bool):
    cursor.execute("SELECT id, name, owner_id FROM public.expenditure_expendituregroup WHERE id != %s", (EXCLUDED_EXPENDITUREGROUP_ID,))
    groups = cursor.fetchall()

    cursor.execute("SELECT expendituregroup_id, user_id FROM public.expenditure_expendituregroup_users")
    members_by_group = {}
    for row in cursor.fetchall():
        members_by_group.setdefault(row["expendituregroup_id"], []).append(row["user_id"])

    cursor.execute(
        "SELECT id, group_id FROM public.expenditure_expenditure WHERE group_id IS NOT NULL AND group_id != %s",
        (EXCLUDED_EXPENDITUREGROUP_ID,),
    )
    links_by_group = {}
    for row in cursor.fetchall():
        links_by_group.setdefault(row["group_id"], []).append(row["id"])

    budget_map = {}
    warnings = []
    links_created = 0

    for g in groups:
        name = canonical_name(g["name"])
        owner = resolve_django_user(g["owner_id"], cli_owner_cognito_uuid)
        if execute:
            row = budget_db.create_budget(owner, {"name": name})
            budget_id = row["id"]
        else:
            budget_id = f"<dry-run-budget-eg-{g['id']}>"
        budget_map[g["id"]] = budget_id

        for member_django_id in members_by_group.get(g["id"], []):
            member = resolve_django_user(member_django_id, cli_owner_cognito_uuid)
            if member == owner:
                continue
            if execute:
                budget_member_db.add_member(owner, budget_id, member)

        for old_expenditure_id in links_by_group.get(g["id"], []):
            entry = txn_id_map.get(("legacy_expenditure", str(old_expenditure_id)))
            if not entry:
                warnings.append(f"expenditure_expendituregroup {g['id']} ({g['name']}): expenditure {old_expenditure_id} was never migrated, skipped")
                continue
            if execute:
                transaction_budget_db.link_budget(entry["user_id"], entry["transaction_id"], budget_id)
            links_created += 1

    return budget_map, warnings, links_created, len(groups)


def main():
    parser = argparse.ArgumentParser(description="Migrate legacy group data into Dompet v2 budgets")
    parser.add_argument("legacy_expenditure_user_id", help="Cognito UUID owning expenditure_expendituregroup's owner_id=1 rows")
    parser.add_argument("--execute", action="store_true", help="Actually write to the database (default: dry run)")
    args = parser.parse_args()

    load_local_env()
    conn = connect()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            txn_id_map = build_transaction_id_map(cursor)

            tg_budget_map, tg_warnings, tg_links, tg_count = migrate_transaction_groups(cursor, txn_id_map, args.execute)
            eg_budget_map, eg_warnings, eg_links, eg_count = migrate_expenditure_groups(
                cursor, args.legacy_expenditure_user_id, txn_id_map, args.execute
            )
        conn.rollback()  # read-only connection; all writes happen via run_atomic in the db.* calls above
    finally:
        conn.close()

    print(f"=== {'EXECUTE' if args.execute else 'DRY RUN'} ===")
    print(f"transaction_groups source:            {tg_count} groups, {tg_links} links created")
    print(f"expenditure_expendituregroup source:  {eg_count} groups (General excluded), {eg_links} links created")

    warnings = tg_warnings + eg_warnings
    print(f"warnings:                             {len(warnings)}")
    if warnings:
        print("\n=== warnings ===")
        for w in warnings:
            print(" ", w)


if __name__ == "__main__":
    main()
