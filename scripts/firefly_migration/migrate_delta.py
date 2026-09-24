"""Delta migration: pulls in only what's NEW in an updated Firefly III dump
since Phase 4's original migrate.py --execute run (2026-09-12).

Standalone from migrate.py on purpose, same reasoning as migrate_budgets.py/
migrate_attachments.py: Phase 4 already executed, and neither
create_transaction nor create_account are idempotent, so a straight re-run
of migrate.py against a newer dump would duplicate all previously-migrated
transactions and accounts, not just the new ones.

Reuses migrate.py's own building blocks directly rather than reimplementing
them:
  - migrate_categories/migrate_tags are ALREADY idempotent (get-or-create by
    name, see app/db/category.py / app/db/tag.py), so they're called
    unmodified on the full (old+new) categories/tags list from the new
    dump -- re-processing already-migrated ones is a safe no-op, and the
    few genuinely new ones get created.
  - migrate_transactions is also reused unmodified, but fed a *filtered*
    ctx["active_journals"] containing only journal ids not already present
    in dompet.transaction_operations.metadata->>'source_id' (the same
    already-migrated check migrate_budgets.py/migrate_attachments.py use).
  - Accounts have no natural-key get-or-create in app.db.account, so this
    script does its own dedup here (not in migrate.py, to avoid silently
    changing migrate.py's own one-time-use behavior): migrate.py's own
    slugify_code(name, firefly_id) convention embeds the Firefly id in
    dompet.accounts.code, so an account is "already migrated" iff a row
    with that exact code already exists for this user.

Assumes the delta is a pure superset (only additions, no edits to
already-migrated rows) -- true for the 09-12 -> 09-22 dump pair this was
built against (verified byte-for-byte), but not a general guarantee for
any future dump pair.

Usage:
    python3 -m scripts.firefly_migration.migrate_delta <new_dump_path> <cognito_user_id> [--execute]
"""

import argparse

from psycopg2.extras import RealDictCursor

from app.utils.env import load_local_env
from app.utils.db import connect
from app.db import account as account_db

from .parse_dump import parse_dump
from .migrate import (
    build_context,
    ensure_currencies,
    migrate_categories,
    migrate_tags,
    migrate_transactions,
    slugify_code,
)


def build_migrated_journal_ids(cursor, user_id: str) -> set:
    cursor.execute(
        """
        SELECT metadata->>'source_id' AS source_id
        FROM dompet.transaction_operations
        WHERE operation_type = 'CREATE' AND metadata->>'source' = 'firefly' AND user_id = %s
        """,
        (str(user_id),),
    )
    return {row["source_id"] for row in cursor.fetchall()}


def build_existing_accounts(cursor, user_id: str) -> tuple:
    cursor.execute("SELECT id, code, name FROM dompet.accounts WHERE user_id = %s", (str(user_id),))
    rows = cursor.fetchall()
    by_code = {row["code"]: row["id"] for row in rows}
    by_name = {}
    for row in rows:
        by_name.setdefault(row["name"].lower(), []).append(row["id"])
    return by_code, by_name


def migrate_accounts_delta(user_id: str, ctx: dict, existing_by_code: dict, existing_by_name: dict, execute: bool):
    """Firefly account ids aren't a stable dedup key on their own: the Phase 6
    consolidation (2026-09-12) deleted 6 duplicate dompet accounts that shared
    a real-world name but had distinct Firefly ids/codes, repointing their
    transactions onto the surviving account. A code-only lookup would treat
    the deleted duplicate's Firefly id as "never migrated" and recreate it.
    Falling back to an exact (case-insensitive) name match catches this --
    safe here because every such collision in this dataset is a genuine
    same-institution duplicate, not two coincidentally-same-named accounts
    (the schema itself allows name dups, so an ambiguous multi-match is left
    to create a new account rather than guessing which one to reuse)."""
    mapping = {}
    created = 0
    ambiguous = []
    for a in ctx["active_accounts"]:
        code = slugify_code(a["name"], a["id"])
        existing_id = existing_by_code.get(code)
        if not existing_id:
            name_matches = existing_by_name.get(a["name"].lower(), [])
            if len(name_matches) == 1:
                existing_id = name_matches[0]
            elif len(name_matches) > 1:
                ambiguous.append(a["name"])
        if existing_id:
            mapping[a["id"]] = existing_id
            continue

        account_type = ctx["account_type_by_id"].get(a["account_type_id"], "Unknown")
        body = {
            "code": code,
            "name": a["name"],
            "description": f"Migrated from Firefly ({account_type})",
        }
        if execute:
            row = account_db.create_account(user_id, body)
            dompet_id = row["id"]
            if a["active"] == "f":
                account_db.deactivate_account(user_id, dompet_id)
        else:
            dompet_id = f"<dry-run-account-{a['id']}>"
        mapping[a["id"]] = dompet_id
        created += 1
    return mapping, created, ambiguous


def main():
    parser = argparse.ArgumentParser(description="Migrate only the new data in an updated Firefly III dump")
    parser.add_argument("dump_path")
    parser.add_argument("user_id", help="Cognito UUID that owns the migrated data")
    parser.add_argument("--execute", action="store_true", help="Actually write to the database (default: dry run)")
    args = parser.parse_args()

    tables = parse_dump(args.dump_path)
    ctx = build_context(tables)

    load_local_env()
    conn = connect()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            migrated_journal_ids = build_migrated_journal_ids(cursor, args.user_id)
            existing_account_codes, existing_account_names = build_existing_accounts(cursor, args.user_id)
        conn.rollback()  # read-only connection; all writes happen via run_atomic in the db.* calls below
    finally:
        conn.close()

    total_journals = len(ctx["active_journals"])
    new_journals = [j for j in ctx["active_journals"] if j["id"] not in migrated_journal_ids]
    ctx["active_journals"] = new_journals

    print(f"=== {'EXECUTE' if args.execute else 'DRY RUN'} ===")
    print(f"journals in dump:       {total_journals}")
    print(f"already migrated:       {total_journals - len(new_journals)}")
    print(f"new journals:           {len(new_journals)}")

    if args.execute:
        conn = connect()
        try:
            with conn:
                with conn.cursor() as cursor:
                    ensure_currencies(cursor)
        finally:
            conn.close()

    account_map, accounts_created, ambiguous_account_names = migrate_accounts_delta(
        args.user_id, ctx, existing_account_codes, existing_account_names, args.execute
    )
    print(f"accounts created:       {accounts_created} (of {len(ctx['active_accounts'])} total in dump)")
    if ambiguous_account_names:
        print(f"ambiguous name matches (created new rather than guessing): {ambiguous_account_names}")

    category_map = migrate_categories(args.user_id, ctx, args.execute)
    print(f"categories mapped:      {len(category_map)} total in dump")

    tag_map = migrate_tags(args.user_id, ctx, args.execute)
    print(f"tags mapped:            {len(tag_map)} total in dump")

    created, skipped, warnings, totals, tag_links = migrate_transactions(
        args.user_id, ctx, account_map, category_map, tag_map, args.execute
    )
    print(f"transactions created:   {created}")
    print(f"transactions skipped:   {len(skipped)}")
    print(f"tag links created:      {tag_links}")
    print(f"warnings:               {len(warnings)}")

    print("\n=== totals by type + currency (new transactions only) ===")
    for (tx_type, currency), total in sorted(totals.items()):
        print(f"  {tx_type:<12} {currency}  {total}")

    if skipped:
        print("\n=== skipped ===")
        for s in skipped:
            print(" ", s)

    if warnings:
        print("\n=== warnings ===")
        for w in warnings:
            print(" ", w)


if __name__ == "__main__":
    main()
