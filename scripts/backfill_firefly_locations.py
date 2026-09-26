"""One-off backfill of dompet.locations + dompet.account_locations derived
from Firefly III data, which has no first-class Location concept of its own.

Two sources of genuine location data, found by inspecting real transaction
names and destination accounts (see the plan/memory notes for the full
manual classification -- brackets in Firefly data are NOT reliably
locations: 'Salary [Nov 2025]' is a date, 'Transfer [HSBC - PBB]' is bank
routing, a bill's destination account like 'Tenaga Nasional Berhad
[Allevia]' has the budget/property name bracketed, not a place):

  Bucket 1: 381 Firefly accounts carry a "[XX] Name" country-code prefix
    (MY/IT/FR/TH) -- Firefly's own convention for a real merchant/place
    account, distinct from bills/loans/banks/budget-labeled accounts.
    Location name = the account name minus its prefix.

  Bucket 2: for other Firefly-sourced transactions with a bracket in the
    name whose destination account is NOT [XX]-prefixed, the bracket text
    is usually the location, unless it's a reference to something else
    already known to the system (see extract_location_name).

Reuses the exact-name get-or-create convention already established by
scripts/legacy_dompet_migration/migrate.py's LocationResolver, and
app.db.account_location.link_location for linking (a payment-instrument
account like "Touch 'n Go eWallet" ending up linked to many locations is
correct -- it represents everywhere that instrument was used, not a 1:1
"this account is that place" claim).

Without --execute this is a pure dry run: prints counts and the full list
of excluded bracket values for a manual sanity check, writes nothing.

Usage:
    python3 -m scripts.backfill_firefly_locations <dump_path> <cognito_user_id> [--execute]
"""

import argparse
import re

from psycopg2.extras import RealDictCursor

from app.utils.env import load_local_env
from app.utils.db import connect, run_atomic
from app.db import account_location as account_location_db

from .firefly_migration.parse_dump import parse_dump
from .firefly_migration.migrate import slugify_code

XX_PREFIX_RE = re.compile(r"^\[[A-Z]{2}\]\s+(.*)$")
BRACKET_RE = re.compile(r"\[(.*?)\]")

CURRENCY_PAIR_RE = re.compile(r"^[A-Z]{3}\s*-\s*[A-Z]{3}$")
MONTH_YEAR_RE = re.compile(r"^[A-Z][a-z]{2,9}\s+\d{4}$")
VEHICLE_PLATE_RE = re.compile(r"^[A-Z]{2,4}\d{3,5}$")

# Firefly account_type values that mean "financial instrument", not a
# merchant/place -- an Expense/Revenue-type account (429+13 of them) is
# nearly always a real merchant, INCLUDING ones with no [XX] prefix (e.g.
# "Daiso", "Publika", "1Utama" are legacy-migrated place accounts that
# happen to share a name with a Firefly bracket -- dropping segments that
# match ANY existing account, tried first, wrongly excluded these).
FINANCIAL_ACCOUNT_TYPES = {"Asset account", "Loan", "Cash account"}

# Bank/wallet abbreviations that show up bracketed but don't exactly match
# the real account name string (e.g. actual account is "MBB Account", not
# "MBB") -- confirmed by checking the Firefly dump before writing this.
FINANCIAL_TOKENS = {"mbb", "hsbc", "yw", "pbb", "tng", "wise", "grabpay", "grab ewallet"}

# Online-only merchants/payees: Expense/Revenue-type accounts (so not
# caught by FINANCIAL_ACCOUNT_TYPES) but not a physical place either.
NON_PHYSICAL_MERCHANTS = {"lhdn", "lazada", "shopee", "steam", "playstation network", "allevia management"}


def build_financial_account_names(tables: dict) -> set:
    account_type_by_id = {t["id"]: t["type"] for t in tables["account_types"]}
    return {
        a["name"].lower()
        for a in tables["accounts"]
        if a["deleted_at"] is None and account_type_by_id.get(a["account_type_id"]) in FINANCIAL_ACCOUNT_TYPES
    }


def get_location_id(name: str) -> str:
    """Exact-name get-or-create, mirrors LocationResolver in
    scripts/legacy_dompet_migration/migrate.py. Uses its own committed
    connection (run_atomic) rather than the caller's read cursor, since
    account_location_db.link_location checks for this row's existence on a
    separate connection immediately afterward -- an uncommitted insert on a
    shared cursor wouldn't be visible there yet (read-committed isolation)."""
    def work(cursor):
        cursor.execute("SELECT id FROM dompet.locations WHERE name = %s LIMIT 1", (name,))
        row = cursor.fetchone()
        if row:
            return row["id"]
        cursor.execute(
            "INSERT INTO dompet.locations (type, name) VALUES ('physical', %s) RETURNING id",
            (name,),
        )
        return cursor.fetchone()["id"]

    return run_atomic(work)


def extract_location_name(bracket_text: str, financial_accounts: set, budgets: set) -> str | None:
    if CURRENCY_PAIR_RE.match(bracket_text) or MONTH_YEAR_RE.match(bracket_text) or VEHICLE_PLATE_RE.match(bracket_text):
        return None

    segments = bracket_text.split(" - ") if " - " in bracket_text else [bracket_text]
    kept = [
        s for s in segments
        if s.strip().lower() not in financial_accounts
        and s.strip().lower() not in budgets
        and s.strip().lower() not in FINANCIAL_TOKENS
        and s.strip().lower() not in NON_PHYSICAL_MERCHANTS
    ]
    if not kept:
        return None
    return " - ".join(kept)


def migrate_bucket_1(cursor, tables: dict, user_id: str, execute: bool):
    accounts = [a for a in tables["accounts"] if a["deleted_at"] is None]
    linked = 0
    skipped_no_account = 0

    for a in accounts:
        m = XX_PREFIX_RE.match(a["name"])
        if not m:
            continue
        location_name = m.group(1)

        code = slugify_code(a["name"], a["id"])
        cursor.execute(
            "SELECT id FROM dompet.accounts WHERE user_id = %s AND code = %s",
            (user_id, code),
        )
        account_row = cursor.fetchone()
        if not account_row:
            skipped_no_account += 1
            continue

        if execute:
            location_id = get_location_id(location_name)
            account_location_db.link_location(user_id, account_row["id"], location_id)
        linked += 1

    return linked, skipped_no_account


def migrate_bucket_2(cursor, tables: dict, user_id: str, execute: bool):
    financial_accounts = build_financial_account_names(tables)
    cursor.execute(
        """
        SELECT LOWER(b.name) AS name FROM dompet.budgets b
        JOIN dompet.budget_members bm ON bm.budget_id = b.id
        WHERE bm.user_id = %s
        """,
        (user_id,),
    )
    budgets = {r["name"] for r in cursor.fetchall()}

    cursor.execute(
        """
        SELECT t.id AS transaction_id, t.name, t.destination_account_id, da.name AS destination_account_name
        FROM dompet.transactions t
        JOIN dompet.operations o ON o.entity_type = 'transaction' AND o.entity_id = t.id AND o.operation_type = 'CREATE'
        JOIN dompet.accounts da ON da.id = t.destination_account_id
        WHERE o.metadata->>'source' = 'firefly'
          AND t.name ~ '\\[.*\\]'
          AND da.name !~ '^\\[[A-Z]{2}\\] '
        """
    )
    rows = cursor.fetchall()

    linked = 0
    excluded = set()
    for row in rows:
        m = BRACKET_RE.search(row["name"])
        if not m:
            continue
        location_name = extract_location_name(m.group(1), financial_accounts, budgets)
        if not location_name:
            excluded.add(m.group(1))
            continue
        if execute:
            location_id = get_location_id(location_name)
            account_location_db.link_location(user_id, row["destination_account_id"], location_id)
        linked += 1

    return linked, sorted(excluded)


def main():
    parser = argparse.ArgumentParser(description="Backfill dompet.locations/account_locations from Firefly data")
    parser.add_argument("dump_path")
    parser.add_argument("user_id", help="Cognito UUID that owns the migrated Firefly data")
    parser.add_argument("--execute", action="store_true", help="Actually write to the database (default: dry run)")
    args = parser.parse_args()

    tables = parse_dump(args.dump_path)

    load_local_env()
    conn = connect()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            b1_linked, b1_skipped = migrate_bucket_1(cursor, tables, args.user_id, args.execute)
            b2_linked, excluded = migrate_bucket_2(cursor, tables, args.user_id, args.execute)
        conn.rollback()  # read-only connection; writes happen via run_atomic in get_location_id/link_location above
    finally:
        conn.close()

    print(f"=== {'EXECUTE' if args.execute else 'DRY RUN'} ===")
    print(f"bucket 1 ([XX]-prefixed accounts): {b1_linked} links, {b1_skipped} skipped (no matching dompet.accounts row, likely merged away)")
    print(f"bucket 2 (free-text bracket parsing): {b2_linked} links, {len(excluded)} distinct excluded bracket values")
    print("\n=== excluded bracket values (bucket 2) ===")
    for e in excluded:
        print(" ", e)


if __name__ == "__main__":
    main()
