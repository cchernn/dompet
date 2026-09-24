"""
One-off Firefly III -> Dompet v2 data migration (Phase 4).

Reads a plain-text pg_dump of a Firefly III database, transforms it into
Dompet v2's schema, and (with --execute) writes it via the same app code
paths already used by the live API:
  - accounts/categories/tags: app.db.account / app.db.category / app.db.tag
    (direct writes)
  - transactions: app.db.transaction_operation.create_transaction, so each
    imported transaction gets a proper append-only CREATE operation record
    with Firefly source IDs preserved in metadata for traceability.
  - tag links: app.db.transaction_tag.link_tag, once the transaction exists.

Without --execute this is a pure dry run: parses and transforms in memory,
prints a summary, and touches no database.

Usage:
    python3 -m scripts.firefly_migration.migrate <dump_path> <cognito_user_id> [--execute]
"""

import argparse
import re
from collections import Counter, defaultdict
from decimal import Decimal, ROUND_HALF_UP

from app.utils.env import load_local_env
from app.utils.db import connect
from app.db import account as account_db
from app.db import category as category_db
from app.db import tag as tag_db
from app.db import transaction_tag as transaction_tag_db
from app.db import transaction_operation

from .parse_dump import parse_dump

TRANSACTION_TYPE_MAP = {
    "Withdrawal": "expenditure",
    "Deposit": "income",
    "Transfer": "transfer",
    "Opening balance": "income",
}

# Currencies referenced by Firefly transaction legs that dompet.currencies
# doesn't already seed (MYR/USD/SGD/EUR/GBP).
ADDITIONAL_CURRENCIES = [
    ("IDR", "Indonesian rupiah", "Rp", 2),
    ("THB", "Thai baht", "฿", 2),
    ("NZD", "New Zealand dollar", "NZ$", 2),
]


def slugify_code(name: str, firefly_id: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "", name).upper()[:20] or "ACCT"
    return f"{slug}-{firefly_id}"


def ensure_currencies(cursor) -> None:
    for code, name, symbol, decimal_places in ADDITIONAL_CURRENCIES:
        cursor.execute(
            """
            INSERT INTO dompet.currencies (code, name, symbol, decimal_places)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (code) DO NOTHING
            """,
            (code, name, symbol, decimal_places),
        )


def build_context(tables: dict) -> dict:
    currency_by_id = {c["id"]: c["code"] for c in tables["transaction_currencies"]}
    account_type_by_id = {t["id"]: t["type"] for t in tables["account_types"]}
    transaction_type_by_id = {t["id"]: t["type"] for t in tables["transaction_types"]}

    active_accounts = [a for a in tables["accounts"] if a["deleted_at"] is None]
    active_categories = [c for c in tables["categories"] if c["deleted_at"] is None]
    active_tags = [t for t in tables["tags"] if t["deleted_at"] is None]
    active_journals = [j for j in tables["transaction_journals"] if j["deleted_at"] is None]

    category_by_journal = {
        link["transaction_journal_id"]: link["category_id"]
        for link in tables["category_transaction_journal"]
    }

    tags_by_journal = defaultdict(list)
    for link in tables["tag_transaction_journal"]:
        tags_by_journal[link["transaction_journal_id"]].append(link["tag_id"])

    legs_by_journal = defaultdict(list)
    for t in tables["transactions"]:
        if t["deleted_at"] is None:
            legs_by_journal[t["transaction_journal_id"]].append(t)

    return {
        "currency_by_id": currency_by_id,
        "account_type_by_id": account_type_by_id,
        "transaction_type_by_id": transaction_type_by_id,
        "active_accounts": active_accounts,
        "active_categories": active_categories,
        "active_tags": active_tags,
        "category_by_journal": category_by_journal,
        "tags_by_journal": tags_by_journal,
        "legs_by_journal": legs_by_journal,
        "active_journals": active_journals,
    }


def migrate_accounts(user_id: str, ctx: dict, execute: bool) -> dict:
    mapping = {}
    for a in ctx["active_accounts"]:
        code = slugify_code(a["name"], a["id"])
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
    return mapping


def migrate_categories(user_id: str, ctx: dict, execute: bool) -> dict:
    mapping = {}
    for c in ctx["active_categories"]:
        body = {"name": c["name"]}
        if execute:
            row = category_db.create_category(user_id, body)
            dompet_id = row["id"]
        else:
            dompet_id = f"<dry-run-category-{c['id']}>"
        mapping[c["id"]] = dompet_id
    return mapping


def migrate_tags(user_id: str, ctx: dict, execute: bool) -> dict:
    mapping = {}
    for t in ctx["active_tags"]:
        body = {"name": t["tag"]}
        if execute:
            row = tag_db.create_tag(user_id, body)
            dompet_id = row["id"]
        else:
            dompet_id = f"<dry-run-tag-{t['id']}>"
        mapping[t["id"]] = dompet_id
    return mapping


def build_transaction(journal: dict, ctx: dict, account_map: dict, category_map: dict):
    """Returns (body, metadata, warning) or (None, None, error) on hard failure."""
    legs = ctx["legs_by_journal"].get(journal["id"], [])
    if len(legs) != 2:
        return None, None, f"journal {journal['id']}: expected 2 active legs, found {len(legs)}"

    source_leg = min(legs, key=lambda leg: Decimal(leg["amount"]))
    dest_leg = max(legs, key=lambda leg: Decimal(leg["amount"]))

    tx_type = TRANSACTION_TYPE_MAP.get(ctx["transaction_type_by_id"].get(journal["transaction_type_id"]))
    if tx_type is None:
        return None, None, f"journal {journal['id']}: unmapped transaction type"

    source_account_id = account_map.get(source_leg["account_id"])
    dest_account_id = account_map.get(dest_leg["account_id"])
    if not source_account_id or not dest_account_id:
        return None, None, f"journal {journal['id']}: references an account outside the migration set"

    currency_code = ctx["currency_by_id"].get(source_leg["transaction_currency_id"])
    if not currency_code:
        return None, None, f"journal {journal['id']}: unknown source currency"

    amount = Decimal(dest_leg["amount"]).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    warning = None
    category_id = None
    firefly_category_id = ctx["category_by_journal"].get(journal["id"])
    if firefly_category_id:
        category_id = category_map.get(firefly_category_id)
        if category_id is None:
            warning = f"journal {journal['id']}: category {firefly_category_id} excluded (soft-deleted), left uncategorized"

    metadata = {
        "source": "firefly",
        "source_id": journal["id"],
        "transaction_group_id": journal["transaction_group_id"],
    }
    if source_leg["transaction_currency_id"] != dest_leg["transaction_currency_id"]:
        metadata["cross_currency"] = {
            "destination_amount": dest_leg["amount"],
            "destination_currency_code": ctx["currency_by_id"].get(dest_leg["transaction_currency_id"]),
        }

    body = {
        "date": journal["date"][:10],
        "name": journal["description"],
        "type": tx_type,
        "amount": str(amount),
        "currency_code": currency_code,
        "category_id": category_id,
        "source_account_id": source_account_id,
        "destination_account_id": dest_account_id,
    }
    return body, metadata, warning


def migrate_transactions(user_id: str, ctx: dict, account_map: dict, category_map: dict, tag_map: dict, execute: bool):
    created = 0
    skipped = []
    warnings = []
    totals = Counter()
    tag_links = 0

    for journal in ctx["active_journals"]:
        body, metadata, note = build_transaction(journal, ctx, account_map, category_map)
        if body is None:
            skipped.append(note)
            continue
        if note:
            warnings.append(note)

        totals[(body["type"], body["currency_code"])] += Decimal(body["amount"])

        firefly_tag_ids = ctx["tags_by_journal"].get(journal["id"], [])
        dompet_tag_ids = []
        for firefly_tag_id in firefly_tag_ids:
            dompet_tag_id = tag_map.get(firefly_tag_id)
            if dompet_tag_id is None:
                warnings.append(f"journal {journal['id']}: tag {firefly_tag_id} excluded (soft-deleted)")
                continue
            dompet_tag_ids.append(dompet_tag_id)

        if execute:
            row = transaction_operation.create_transaction(user_id, body, metadata=metadata)
            for dompet_tag_id in dompet_tag_ids:
                transaction_tag_db.link_tag(user_id, row["id"], dompet_tag_id)
        tag_links += len(dompet_tag_ids)
        created += 1

    return created, skipped, warnings, totals, tag_links


def main():
    parser = argparse.ArgumentParser(description="Migrate a Firefly III dump into Dompet v2")
    parser.add_argument("dump_path")
    parser.add_argument("user_id", help="Cognito UUID that will own the migrated data")
    parser.add_argument("--execute", action="store_true", help="Actually write to the database (default: dry run)")
    args = parser.parse_args()

    tables = parse_dump(args.dump_path)
    ctx = build_context(tables)

    print(f"=== {'EXECUTE' if args.execute else 'DRY RUN'} ===")
    print(f"accounts to migrate:    {len(ctx['active_accounts'])}")
    print(f"categories to migrate:  {len(ctx['active_categories'])}")
    print(f"tags to migrate:        {len(ctx['active_tags'])}")
    print(f"journals to migrate:    {len(ctx['active_journals'])}")

    if args.execute:
        load_local_env()
        conn = connect()
        try:
            with conn:
                with conn.cursor() as cursor:
                    ensure_currencies(cursor)
        finally:
            conn.close()
        print("ensured additional currencies (IDR, THB, NZD)")

    account_map = migrate_accounts(args.user_id, ctx, args.execute)
    print(f"accounts mapped:        {len(account_map)}")

    category_map = migrate_categories(args.user_id, ctx, args.execute)
    print(f"categories mapped:      {len(category_map)}")

    tag_map = migrate_tags(args.user_id, ctx, args.execute)
    print(f"tags mapped:            {len(tag_map)}")

    created, skipped, warnings, totals, tag_links = migrate_transactions(
        args.user_id, ctx, account_map, category_map, tag_map, args.execute
    )
    print(f"transactions created:   {created}")
    print(f"transactions skipped:   {len(skipped)}")
    print(f"tag links created:      {tag_links}")
    print(f"warnings:               {len(warnings)}")

    print("\n=== totals by type + currency ===")
    for (tx_type, currency), total in sorted(totals.items()):
        print(f"  {tx_type:<12} {currency}  {total}")

    if skipped:
        print("\n=== skipped (first 20) ===")
        for s in skipped[:20]:
            print(" ", s)

    if warnings:
        print("\n=== warnings (first 20) ===")
        for w in warnings[:20]:
            print(" ", w)


if __name__ == "__main__":
    main()
