"""
One-off legacy Dompet (pre-v2 Supabase schema) -> Dompet v2 data migration (Phase 5).

Sources (all in the `public` schema of the same Supabase project):
  - public.transactions            current legacy schema; migrates every
                                    distinct Cognito UUID found in its `user`
                                    column (real per-row ownership already).
  - public.locations               referenced by public.transactions.location.
  - public.expenditure_expenditure older Django-era predecessor table, single
                                    legacy integer user_id=1, mapped to the
                                    Cognito UUID given on the command line.
                                    type='receive' rows are excluded (data
                                    quality issue: names are overwhelmingly
                                    ordinary purchases, not income) and
                                    written to a review report instead.

Writes via the same app code paths as the live API:
  - accounts/categories/locations: app.db.account / app.db.category /
    app.db.location (direct writes; category creation is get-or-create)
  - transactions: app.db.transaction_operation.create_transaction, so each
    imported row gets a proper append-only CREATE operation with source IDs
    preserved in metadata for traceability.

Without --execute this is a pure dry run against a read-only snapshot of the
live public.* tables: no writes happen.

Usage:
    python3 -m scripts.legacy_dompet_migration.migrate <legacy_expenditure_user_id_1_cognito_uuid> [--execute] [--report-path PATH]
"""

import argparse
import re
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP

from psycopg2.extras import RealDictCursor

from app.utils.env import load_local_env
from app.utils.db import connect, run_atomic
from app.db import category as category_db
from app.db import transaction_operation

CURRENCY_NORMALIZE = {"NTD": "TWD"}

# public.transactions rows confirmed (2026-09-12) to be double-entries of the
# same real-world purchase already present in the Firefly dump, from the
# 2025-09-25..2025-10-05 window where both apps were used in parallel during
# the switch to Firefly. Matched by exact date+type+currency+amount plus a
# manual name check (e.g. legacy 'Shell' == firefly 'Shell [Segambut]').
# Excluding these here so Phase 4 (Firefly) is the sole source for them.
DUPLICATE_OF_FIREFLY_TRANSACTION_IDS = {
    1334, 1335, 1336, 1337, 1338, 1339, 1340, 1341, 1342,
    1343, 1344, 1345, 1346, 1347, 1349, 1350,
}

ADDITIONAL_CURRENCIES = [
    ("NZD", "New Zealand dollar", "NZ$", 2),
    ("TWD", "New Taiwan dollar", "NT$", 2),
    ("IDR", "Indonesian rupiah", "Rp", 2),
    ("KRW", "South Korean won", "₩", 2),
    ("VND", "Vietnamese dong", "₫", 2),
    ("THB", "Thai baht", "฿", 2),
]

TRANSFER_ACTION_WORDS = {"TopUp", "Reload", "Transfer", "Payment", "Withdrawal"}
TRANSFER_NAME_OVERRIDES = {"ATM Cash Withdrawal": "Cash"}
UNMAPPED_ACCOUNT_NAME = "Unmapped"

EXPENDITURE_EXPENDITURE_TYPE_MAP = {
    "spend": "expenditure",
    "transfer": "transfer",
}


def normalize_currency(code: str) -> str:
    return CURRENCY_NORMALIZE.get(code, code)


def parse_transfer_destination(name: str):
    if name in TRANSFER_NAME_OVERRIDES:
        return TRANSFER_NAME_OVERRIDES[name]
    tokens = name.split()
    if tokens and tokens[-1] in TRANSFER_ACTION_WORDS:
        dest = " ".join(tokens[:-1]).strip()
        return dest or None
    return None


def slugify(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "", name).upper()[:20] or "ACCT"


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


class AccountResolver:
    """Get-or-create dompet accounts by (user_id, name), idempotent across runs."""

    def __init__(self, execute: bool):
        self.execute = execute
        self.cache = {}
        self.counter = 0

    def resolve(self, user_id: str, name: str, description: str = None) -> str:
        key = (str(user_id), name)
        if key in self.cache:
            return self.cache[key]

        if not self.execute:
            self.counter += 1
            account_id = f"<dry-run-account-{self.counter}>"
            self.cache[key] = account_id
            return account_id

        def work(cursor):
            cursor.execute(
                "SELECT id FROM dompet.accounts WHERE user_id = %s AND name = %s LIMIT 1",
                (str(user_id), name),
            )
            row = cursor.fetchone()
            if row:
                return row["id"]

            base_code = slugify(name)
            for attempt in range(1, 50):
                candidate_code = base_code if attempt == 1 else f"{base_code}-{attempt}"
                cursor.execute(
                    "SELECT 1 FROM dompet.accounts WHERE user_id = %s AND code = %s",
                    (str(user_id), candidate_code),
                )
                if not cursor.fetchone():
                    cursor.execute(
                        """
                        INSERT INTO dompet.accounts (user_id, code, name, description)
                        VALUES (%s, %s, %s, %s)
                        RETURNING id
                        """,
                        (str(user_id), candidate_code, name, description),
                    )
                    return cursor.fetchone()["id"]
            raise RuntimeError(f"could not find a free account code for {name!r}")

        account_id = run_atomic(work)
        self.cache[key] = account_id
        return account_id

    def unmapped(self, user_id: str) -> str:
        return self.resolve(user_id, UNMAPPED_ACCOUNT_NAME, "Migration fallback for an unresolved counterparty")


class CategoryResolver:
    def __init__(self, execute: bool):
        self.execute = execute
        self.cache = {}
        self.counter = 0

    def resolve(self, user_id: str, name: str) -> str:
        key = (str(user_id), name)
        if key in self.cache:
            return self.cache[key]
        if not self.execute:
            self.counter += 1
            category_id = f"<dry-run-category-{self.counter}>"
        else:
            row = category_db.create_category(user_id, {"name": name})
            category_id = row["id"]
        self.cache[key] = category_id
        return category_id


class LocationResolver:
    """Get-or-create dompet locations by name (locations are global, not per-user)."""

    def __init__(self, execute: bool):
        self.execute = execute
        self.cache = {}
        self.counter = 0

    def resolve(self, name: str, loc_type: str, google_maps_url: str = None, url: str = None) -> str:
        if name in self.cache:
            return self.cache[name]
        if not self.execute:
            self.counter += 1
            location_id = f"<dry-run-location-{self.counter}>"
            self.cache[name] = location_id
            return location_id

        def work(cursor):
            cursor.execute("SELECT id FROM dompet.locations WHERE name = %s LIMIT 1", (name,))
            row = cursor.fetchone()
            if row:
                return row["id"]
            cursor.execute(
                """
                INSERT INTO dompet.locations (type, name, google_maps_url, url)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (loc_type, name, google_maps_url, url),
            )
            return cursor.fetchone()["id"]

        location_id = run_atomic(work)
        self.cache[name] = location_id
        return location_id


def fetch_legacy_data(cursor):
    cursor.execute("""
        SELECT id, "user", date, name, type, amount, currency, payment_method, category, location
        FROM public.transactions
    """)
    transactions = cursor.fetchall()

    cursor.execute("""
        SELECT id, name, url, google_page_link, google_maps_link, category, access_type
        FROM public.locations
    """)
    locations = cursor.fetchall()

    cursor.execute("""
        SELECT id, date, name, location, type, amount, currency, payment_method, category, group_id
        FROM public.expenditure_expenditure
    """)
    legacy_expenditures = cursor.fetchall()

    return transactions, locations, legacy_expenditures


def migrate_locations(locations, location_resolver):
    """Returns {legacy_location_id: {"dompet_id": ..., "name": ...}}"""
    mapping = {}
    for loc in locations:
        loc_type = "physical" if loc["access_type"] == "onsite" else "online"
        google_maps_url = loc["google_maps_link"] or None
        url = loc["url"] or None
        if loc_type == "physical" and not google_maps_url:
            # can't satisfy the CHECK constraint; skip, transactions referencing
            # it fall back to the Unmapped account.
            continue
        if loc_type == "online" and not url:
            continue
        dompet_id = location_resolver.resolve(loc["name"], loc_type, google_maps_url, url)
        mapping[loc["id"]] = {"dompet_id": dompet_id, "name": loc["name"]}
    return mapping


def build_public_transaction(row, account_resolver, category_resolver, location_map, warnings):
    user_id = row["user"]
    tx_type = row["type"]
    currency_code = normalize_currency(row["currency"])
    category_id = category_resolver.resolve(user_id, row["category"]) if row["category"] else None
    payment_account_id = account_resolver.resolve(user_id, row["payment_method"])

    metadata = {"source": "legacy_dompet", "source_id": row["id"]}

    if tx_type == "expenditure":
        source_account_id = payment_account_id
        location_entry = location_map.get(row["location"]) if row["location"] else None
        if location_entry:
            destination_account_id = account_resolver.resolve(
                user_id, location_entry["name"], "Migrated from a legacy Dompet location"
            )
        else:
            destination_account_id = account_resolver.unmapped(user_id)

    elif tx_type == "transfer":
        source_account_id = payment_account_id
        dest_name = parse_transfer_destination(row["name"])
        if dest_name:
            destination_account_id = account_resolver.resolve(user_id, dest_name)
        else:
            destination_account_id = account_resolver.unmapped(user_id)
            warnings.append(f"legacy_dompet transaction {row['id']}: unresolved transfer destination in {row['name']!r}")

    else:
        return None, None, f"legacy_dompet transaction {row['id']}: unmapped type {tx_type!r}"

    body = {
        "date": row["date"].isoformat(),
        "name": row["name"],
        "type": tx_type,
        "amount": str(Decimal(row["amount"]).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        "currency_code": currency_code,
        "category_id": category_id,
        "source_account_id": source_account_id,
        "destination_account_id": destination_account_id,
    }
    return body, metadata, None


def build_legacy_expenditure_transaction(row, cognito_user_id, account_resolver, category_resolver, warnings):
    raw_type = row["type"]
    tx_type = EXPENDITURE_EXPENDITURE_TYPE_MAP.get(raw_type)
    if tx_type is None:
        tx_type = "expenditure"
        warnings.append(f"legacy_expenditure {row['id']}: unmapped type {raw_type!r}, defaulted to expenditure")

    currency_code = normalize_currency(row["currency"])
    category_id = category_resolver.resolve(cognito_user_id, row["category"]) if row["category"] else None
    payment_account_id = account_resolver.resolve(cognito_user_id, row["payment_method"])

    name = row["name"]
    if row["location"]:
        name = f"{name} ({row['location']})"

    metadata = {
        "source": "legacy_expenditure",
        "source_id": row["id"],
        "legacy_group_id": row["group_id"],
    }

    if tx_type == "transfer":
        source_account_id = payment_account_id
        dest_name = parse_transfer_destination(row["name"])
        if dest_name:
            destination_account_id = account_resolver.resolve(cognito_user_id, dest_name)
        else:
            destination_account_id = account_resolver.unmapped(cognito_user_id)
            warnings.append(f"legacy_expenditure {row['id']}: unresolved transfer destination in {row['name']!r}")
    else:
        source_account_id = payment_account_id
        destination_account_id = account_resolver.unmapped(cognito_user_id)

    body = {
        "date": row["date"].isoformat(),
        "name": name,
        "type": tx_type,
        "amount": str(Decimal(row["amount"]).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        "currency_code": currency_code,
        "category_id": category_id,
        "source_account_id": source_account_id,
        "destination_account_id": destination_account_id,
    }
    return body, metadata


def main():
    parser = argparse.ArgumentParser(description="Migrate the legacy Dompet Supabase schema into Dompet v2")
    parser.add_argument("legacy_expenditure_user_id", help="Cognito UUID owning expenditure_expenditure's user_id=1 rows")
    parser.add_argument("--execute", action="store_true", help="Actually write to the database (default: dry run)")
    parser.add_argument("--report-path", default="legacy_migration_excluded_rows.txt")
    args = parser.parse_args()

    load_local_env()
    conn = connect()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            transactions_all, locations, legacy_expenditures_all = fetch_legacy_data(cursor)
            cursor.execute("""
                SELECT id, name, category, amount, currency, date
                FROM public.expenditure_expenditure WHERE type = 'receive'
                ORDER BY date
            """)
            excluded_receive_rows = cursor.fetchall()
            cursor.execute("""
                SELECT id, name, category, amount, currency, date
                FROM public.transactions WHERE type = 'income'
                ORDER BY date
            """)
            excluded_income_rows = cursor.fetchall()
            cursor.execute("""
                SELECT id, name, category, amount, currency, date
                FROM public.transactions WHERE id = ANY(%s)
                ORDER BY date
            """, (list(DUPLICATE_OF_FIREFLY_TRANSACTION_IDS),))
            excluded_duplicate_rows = cursor.fetchall()
        conn.rollback()  # read-only so far; no writes intended from this connection
    finally:
        conn.close()

    # Both public.transactions and expenditure_expenditure show the same data
    # quality issue: 'income'/'receive' rows are overwhelmingly mislabeled
    # ordinary purchases (see e.g. "Thai Nyonya BBQ" tagged as income). Both
    # are excluded here and written to a combined review report instead of
    # being trusted at face value.
    transactions = [
        r for r in transactions_all
        if r["type"] != "income" and r["id"] not in DUPLICATE_OF_FIREFLY_TRANSACTION_IDS
    ]
    legacy_expenditures = [r for r in legacy_expenditures_all if r["type"] != "receive"]

    print(f"=== {'EXECUTE' if args.execute else 'DRY RUN'} ===")
    print(f"public.transactions rows (total):     {len(transactions_all)}")
    print(f"  excluded (type='income'):            {len(excluded_income_rows)}")
    print(f"  excluded (duplicate of firefly):     {len(excluded_duplicate_rows)}")
    print(f"  to migrate:                          {len(transactions)}")
    print(f"public.locations rows:                {len(locations)}")
    print(f"expenditure_expenditure rows (total): {len(legacy_expenditures_all)}")
    print(f"  excluded (type='receive'):           {len(excluded_receive_rows)}")
    print(f"  to migrate:                          {len(legacy_expenditures)}")

    if args.execute:
        conn = connect()
        try:
            with conn:
                with conn.cursor() as cursor:
                    ensure_currencies(cursor)
        finally:
            conn.close()
        print("ensured additional currencies (NZD, TWD, IDR, KRW, VND, THB)")

    account_resolver = AccountResolver(args.execute)
    category_resolver = CategoryResolver(args.execute)
    location_resolver = LocationResolver(args.execute)

    location_map = migrate_locations(locations, location_resolver)
    print(f"locations mapped: {len(location_map)} / {len(locations)}")

    warnings = []
    skipped = []
    created = 0
    totals = Counter()

    for row in transactions:
        body, metadata, error = build_public_transaction(row, account_resolver, category_resolver, location_map, warnings)
        if error:
            skipped.append(error)
            continue
        totals[(row["user"], body["type"], body["currency_code"])] += Decimal(body["amount"])
        if args.execute:
            transaction_operation.create_transaction(row["user"], body, metadata=metadata)
        created += 1

    for row in legacy_expenditures:
        body, metadata = build_legacy_expenditure_transaction(
            row, args.legacy_expenditure_user_id, account_resolver, category_resolver, warnings
        )
        totals[(args.legacy_expenditure_user_id, body["type"], body["currency_code"])] += Decimal(body["amount"])
        if args.execute:
            transaction_operation.create_transaction(args.legacy_expenditure_user_id, body, metadata=metadata)
        created += 1

    print(f"\ntransactions created: {created}")
    print(f"transactions skipped: {len(skipped)}")
    print(f"warnings:             {len(warnings)}")
    print(f"accounts resolved:    {len(account_resolver.cache)}")
    print(f"categories resolved:  {len(category_resolver.cache)}")

    print("\n=== totals by user + type + currency ===")
    for (user_id, tx_type, currency), total in sorted(totals.items()):
        print(f"  {user_id}  {tx_type:<12} {currency}  {total}")

    if skipped:
        print("\n=== skipped (first 20) ===")
        for s in skipped[:20]:
            print(" ", s)

    if warnings:
        print("\n=== warnings (first 20) ===")
        for w in warnings[:20]:
            print(" ", w)

    total_excluded = len(excluded_income_rows) + len(excluded_receive_rows) + len(excluded_duplicate_rows)
    if total_excluded:
        with open(args.report_path, "w") as f:
            f.write("Excluded rows for manual review\n")
            f.write("reason\tsource\tid\tdate\tname\tcategory\tamount\tcurrency\n")
            for r in excluded_income_rows:
                f.write(f"mislabeled_income\tpublic.transactions\t{r['id']}\t{r['date']}\t{r['name']}\t{r['category']}\t{r['amount']}\t{r['currency']}\n")
            for r in excluded_receive_rows:
                f.write(f"mislabeled_income\texpenditure_expenditure\t{r['id']}\t{r['date']}\t{r['name']}\t{r['category']}\t{r['amount']}\t{r['currency']}\n")
            for r in excluded_duplicate_rows:
                f.write(f"duplicate_of_firefly\tpublic.transactions\t{r['id']}\t{r['date']}\t{r['name']}\t{r['category']}\t{r['amount']}\t{r['currency']}\n")
        print(f"\nwrote {total_excluded} excluded rows to {args.report_path}")


if __name__ == "__main__":
    main()
