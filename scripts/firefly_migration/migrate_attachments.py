"""One-off migration of Firefly III's real attachment files into Dompet v2.

Standalone from migrate.py on purpose -- see migrate_budgets.py's docstring
for why (Phase 4 already executed; create_transaction is not idempotent).
This script only touches dompet.attachments/transaction_attachments,
resolving already-migrated transactions via
transaction_operations.metadata->>'source_id', exactly like
migrate_budgets.py does for budgets.

Firefly's `attachments` table is polymorphic (attachable_type/attachable_id)
but in this dataset every row's attachable_type is TransactionJournal, so
attachable_id is always a Firefly transaction_journals.id. Rows with
deleted_at set (soft-deleted) or uploaded='f' (upload never completed, no
real file) are skipped -- the remainder matches the tarball's real files
1:1.

Unlike budgets/tags/categories, dompet.attachments has no unique-name-style
natural key to dedupe on, so create_attachment_record isn't idempotent on
its own. This script tags every row it creates with
metadata={"source": "firefly", "source_id": <firefly attachment id>}
(migration 021 added the column) and checks for that tag before creating,
so a re-run after a partial failure (e.g. a network error mid-upload) skips
already-migrated rows instead of duplicating them. It also verifies the S3
object actually exists on a "found existing row" hit, re-uploading only if
it's actually missing -- covering the case where the DB row committed but
the upload itself failed.

Usage:
    python3 -m scripts.firefly_migration.migrate_attachments <dump_path> <tarball_path> <cognito_user_id> [--execute]
"""

import argparse
import os
import tarfile

import boto3
from botocore.exceptions import ClientError
from psycopg2.extras import RealDictCursor

from app.utils.env import load_local_env
from app.utils.db import connect
from app.db import attachment as attachment_db
from app.db import transaction_attachment as transaction_attachment_db

from .parse_dump import parse_dump

TARBALL_MEMBER = "attachments/at-{id}.data"


def build_journal_id_map(cursor, user_id: str) -> dict:
    cursor.execute(
        """
        SELECT transaction_id, metadata->>'source_id' AS source_id
        FROM dompet.transaction_operations
        WHERE operation_type = 'CREATE' AND metadata->>'source' = 'firefly' AND user_id = %s
        """,
        (str(user_id),),
    )
    return {row["source_id"]: row["transaction_id"] for row in cursor.fetchall()}


def find_existing(cursor, firefly_id: str) -> dict:
    cursor.execute(
        "SELECT id, storage_key FROM dompet.attachments WHERE metadata->>'source' = 'firefly' AND metadata->>'source_id' = %s",
        (firefly_id,),
    )
    return cursor.fetchone()


def s3_object_exists(s3, bucket: str, key: str) -> bool:
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as e:
        # Without s3:ListBucket, S3 can't tell the caller "not found" without
        # leaking whether the key exists, so a missing object under a prefix
        # we otherwise have working Put/Get/Head access to also comes back
        # as 403, not 404.
        if e.response["Error"]["Code"] in ("404", "NoSuchKey", "403"):
            return False
        raise


def main():
    parser = argparse.ArgumentParser(description="Migrate Firefly III attachment files into Dompet v2")
    parser.add_argument("dump_path")
    parser.add_argument("tarball_path")
    parser.add_argument("user_id", help="Cognito UUID that owns the migrated attachments")
    parser.add_argument("--execute", action="store_true", help="Actually write to the database/S3 (default: dry run)")
    args = parser.parse_args()

    tables = parse_dump(args.dump_path)
    all_rows = tables["attachments"]

    soft_deleted = [r for r in all_rows if r["deleted_at"] is not None]
    never_uploaded = [r for r in all_rows if r["uploaded"] != "t"]
    candidates = [r for r in all_rows if r["deleted_at"] is None and r["uploaded"] == "t"]

    load_local_env()
    conn = connect()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            journal_id_map = build_journal_id_map(cursor, args.user_id)
            existing_by_source_id = {}
            if args.execute:
                for row in candidates:
                    existing = find_existing(cursor, row["id"])
                    if existing:
                        existing_by_source_id[row["id"]] = existing
        conn.rollback()  # read-only connection; all writes happen via run_atomic in the db.* calls below
    finally:
        conn.close()

    bucket = os.getenv("ATTACHMENTS_S3_BUCKET")
    # Not a Lambda execution context here (running locally), so there's no
    # implicit IAM role to pick up credentials from -- use the same named
    # profile Setup.py uses for every other AWS-touching local script.
    s3 = boto3.Session(profile_name="dompet-user").client("s3")
    tar = tarfile.open(args.tarball_path, "r:gz")

    warnings = []
    created = 0
    reused = 0
    re_uploaded = 0
    linked = 0

    for row in candidates:
        firefly_id = row["id"]
        dompet_txn_id = journal_id_map.get(row["attachable_id"])
        if not dompet_txn_id:
            warnings.append(f"attachment {firefly_id} ({row['filename']}): journal {row['attachable_id']} was never migrated, skipped")
            continue

        if not args.execute:
            continue

        existing = existing_by_source_id.get(firefly_id)
        if existing:
            attachment_id = existing["id"]
            storage_key = existing["storage_key"]
            reused += 1
            if not s3_object_exists(s3, bucket, storage_key):
                data = tar.extractfile(TARBALL_MEMBER.format(id=firefly_id)).read()
                s3.put_object(
                    Bucket=bucket,
                    Key=storage_key,
                    Body=data,
                    ContentType=row["mime"],
                )
                re_uploaded += 1
        else:
            new_row = attachment_db.create_attachment_record(
                args.user_id,
                row["filename"],
                content_type=row["mime"],
                size_bytes=int(row["size"]),
                metadata={"source": "firefly", "source_id": firefly_id},
            )
            attachment_id = new_row["id"]
            storage_key = new_row["storage_key"]
            created += 1

            data = tar.extractfile(TARBALL_MEMBER.format(id=firefly_id)).read()
            s3.put_object(
                Bucket=bucket,
                Key=storage_key,
                Body=data,
                ContentType=row["mime"],
            )

        transaction_attachment_db.link_attachment(args.user_id, dompet_txn_id, attachment_id)
        linked += 1

    tar.close()

    print(f"=== {'EXECUTE' if args.execute else 'DRY RUN'} ===")
    print(f"total rows:          {len(all_rows)}")
    print(f"soft-deleted skipped:{len(soft_deleted):>4}")
    print(f"never-uploaded skip: {len(never_uploaded):>4}")
    print(f"candidates:          {len(candidates)}")
    print(f"created:             {created}")
    print(f"reused (resume):     {reused}")
    print(f"re-uploaded on resume:{re_uploaded}")
    print(f"linked:              {linked}")
    print(f"warnings:            {len(warnings)}")
    if warnings:
        print("\n=== warnings ===")
        for w in warnings:
            print(" ", w)


if __name__ == "__main__":
    main()
