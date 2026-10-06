"""One-off cleanup: dedupes attachments that were independently migrated
from Firefly as separate dompet.attachments rows despite being
byte-identical files (same md5 in the source dump), each linked to a
different transaction.

For each duplicate pair, keeps the lower-Firefly-id attachment as
canonical, links the other pair's transaction to it too (the existing
transaction_attachments junction already supports one attachment linked
to many transactions), then deletes the duplicate attachment row and its
S3 object -- exactly what DELETE /attachments/{id} already does
(app.db.attachment.delete_attachment + app.utils.s3.delete_object). The
stale transaction_attachments link to the deleted duplicate cleans up
automatically via its ON DELETE CASCADE FK.

Usage:
    python3 -m scripts.dedupe_attachments <dump_path> <cognito_user_id> [--execute]
"""

import argparse
import os
from collections import defaultdict

import boto3
from psycopg2.extras import RealDictCursor

from app.utils.env import load_local_env
from app.utils.db import connect
from app.db import attachment as attachment_db
from app.db import transaction_attachment as transaction_attachment_db

from .firefly_migration.parse_dump import parse_dump


def find_duplicate_groups(tables: dict) -> list:
    by_md5 = defaultdict(list)
    for a in tables["attachments"]:
        if a["deleted_at"] is None and a["uploaded"] == "t":
            by_md5[a["md5"]].append(a["id"])
    return [sorted(ids, key=int) for ids in by_md5.values() if len(ids) > 1]


def build_plan(cursor, groups: list) -> list:
    all_firefly_ids = [fid for group in groups for fid in group]
    cursor.execute(
        "SELECT metadata->>'source_id' AS firefly_id, id, storage_key FROM dompet.attachments WHERE metadata->>'source_id' = ANY(%s)",
        (all_firefly_ids,),
    )
    dompet_by_firefly = {row["firefly_id"]: (row["id"], row["storage_key"]) for row in cursor.fetchall()}

    plan = []
    for group in groups:
        canonical = dompet_by_firefly.get(group[0])
        if not canonical:
            continue
        canonical_id, _ = canonical

        for dup_firefly_id in group[1:]:
            dup = dompet_by_firefly.get(dup_firefly_id)
            if not dup:
                continue
            dup_id, dup_storage_key = dup

            cursor.execute(
                "SELECT transaction_id FROM dompet.transaction_attachments WHERE attachment_id = %s",
                (str(dup_id),),
            )
            dup_txn_ids = [row["transaction_id"] for row in cursor.fetchall()]
            plan.append((canonical_id, dup_id, dup_storage_key, dup_txn_ids))
    return plan


def main():
    parser = argparse.ArgumentParser(description="Dedupe byte-identical Firefly-sourced attachments")
    parser.add_argument("dump_path")
    parser.add_argument("user_id", help="Cognito UUID that owns the attachments")
    parser.add_argument("--execute", action="store_true", help="Actually write to the database/S3 (default: dry run)")
    args = parser.parse_args()

    tables = parse_dump(args.dump_path)
    groups = find_duplicate_groups(tables)

    load_local_env()
    conn = connect()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            plan = build_plan(cursor, groups)
        conn.rollback()  # read-only connection; all writes happen via run_atomic in the db.* calls below
    finally:
        conn.close()

    s3 = boto3.Session(profile_name="dompet-user").client("s3")
    bucket = os.getenv("ATTACHMENTS_S3_BUCKET")

    relinked = 0
    deleted = 0
    for canonical_id, dup_id, dup_storage_key, dup_txn_ids in plan:
        for txn_id in dup_txn_ids:
            if args.execute:
                transaction_attachment_db.link_attachment(args.user_id, txn_id, canonical_id)
            relinked += 1

        if args.execute:
            attachment_db.delete_attachment(args.user_id, dup_id)
            s3.delete_object(Bucket=bucket, Key=dup_storage_key)
        deleted += 1

    print(f"=== {'EXECUTE' if args.execute else 'DRY RUN'} ===")
    print(f"duplicate groups found:              {len(groups)}")
    print(f"pairs resolved:                      {len(plan)}")
    print(f"transactions relinked to canonical:   {relinked}")
    print(f"duplicate attachments removed:        {deleted}")


if __name__ == "__main__":
    main()
