import os
import boto3
import shutil
import subprocess
import argparse
from Database import BaseDatabase

def upload():
    uploadLambda()

def migrate():
    db = BaseDatabase()
    createAttachmentTable(db)
    createLocationTable(db)
    createTransactionTable(db)
    createTransactionGroupTable(db)
    createTransactionTransactionGroupTable(db)
    createUserTransactionGroupTable(db)
    createTransactionAttachmentTable(db)

def uploadLambda():
    repo_url = os.getenv('GIT_REPO_URL')
    repo_branch = os.getenv('GIT_REPO_BRANCH')
    repo_dir = "/tmp/dompet"
    zip_path = "/tmp/dompet.zip"
    function_name = "dompet"

    subprocess.run(["git", "clone", "--branch", repo_branch, repo_url, repo_dir], check=True)
    shutil.make_archive("/tmp/dompet", "zip", repo_dir)

    session = boto3.Session(profile_name="dompet-user")
    client = session.client("lambda")
    with open(zip_path, "rb") as fp:
        zip_content = fp.read()
    
    response = client.update_function_code(
        FunctionName=function_name,
        ZipFile=zip_content
    )

    shutil.rmtree(repo_dir)
    os.remove(zip_path)


def createTransactionTable(db):
    db.create("transactions", [
        ("user", "UUID NOT NULL"),
        ("date", "DATE NOT NULL"),
        ("name", "VARCHAR(255)"),
        ("location", "INT REFERENCES locations (id) ON DELETE NO ACTION"),
        ("type", "VARCHAR(255) DEFAULT 'expenditure'"),
        ("amount", "DECIMAL(10,2) NOT NULL DEFAULT 0.00 CHECK (amount >= 0)"),
        ("currency", "VARCHAR(3) DEFAULT 'MYR'"),
        ("payment_method", "VARCHAR(255)"),
        ("category", "VARCHAR(255) DEFAULT 'others'"),
        ("is_active", "BOOLEAN DEFAULT TRUE"),
    ])

def createTransactionGroupTable(db):
    db.create("transaction_groups", [
        ("user", "UUID NOT NULL"),
        ("name", "VARCHAR(255)"),
        ("is_active", "BOOLEAN DEFAULT TRUE"),
    ])

def createTransactionTransactionGroupTable(db):
    db.createJunction("transaction_transaction_group",
        "transaction_id",
        "transactions",
        "transaction_group_id",
        "transaction_groups"
    )

def createUserTransactionGroupTable(db):
    db.createJunctionUser("user_transaction_group",
        "transaction_group_id",
        "transaction_groups"
    )

def createAttachmentTable(db):
    db.create("attachments", [
        ("user", "UUID NOT NULL"),
        ("date", "DATE NOT NULL"),
        ("name", "VARCHAR(255)"),
        ("filename", "VARCHAR(255)"),
        ("url", "VARCHAR(255)"),
        ("type", "VARCHAR(255)"),
        ("is_active", "BOOLEAN DEFAULT TRUE"),
    ])

def createTransactionAttachmentTable(db):
    db.createJunction("transaction_attachment",
        "transaction_id",
        "transactions",
        "attachment_id",
        "attachments"
    )

def createLocationTable(db):
    db.create("locations", [
        ("date", "DATE NOT NULL"),
        ("name", "VARCHAR(255)"),
        ("url", "VARCHAR(255)"),
        ("google_page_link", "VARCHAR(255)"),
        ("google_maps_link", "VARCHAR(255)"),
        ("category", "VARCHAR(255)"),
        ("access_type", "VARCHAR(255) NOT NULL DEFAULT 'onsite'"),
        ("is_active", "BOOLEAN DEFAULT TRUE"),
    ])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="""
        upload: pushes changes to AWS Lambda
        migrate: create databases
        """,
        add_help=True
    )
    parser.add_argument(
        "command",
        choices=[
            "upload",
            "migrate"
        ],
        help="Setup commands to run"
    )

    args = parser.parse_args()

    if args.command == "upload":
        upload()
    if args.command == "migrate":
        migrate()