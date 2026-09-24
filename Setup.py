import os
import re
import boto3
import shutil
import subprocess
import argparse
import tempfile
import time
import zipfile

from app.utils.env import load_local_env

# Local-deployment-only paths that Lambda never needs (it only runs
# app/routes + app/response_handler::lambda_handler and their dependencies).
LAMBDA_ZIP_EXCLUDES = {
    "Dockerfile",
    "docker-compose.yml",
    "requirements-local.txt",
    "app/server.py",
    "scripts/deploy",
    "archive",
    ".git",
    ".venv",
    "__pycache__",
}

# The Lambda's actual deployed runtime (confirmed via `aws lambda
# get-function-configuration`) -- also a hard ceiling: app/lib/params.py
# imports the stdlib `cgi` module, which was removed in Python 3.13.
LAYER_NAME = "dompet-layer"
LAYER_RUNTIME = "python3.10"
LAYER_PYTHON_VERSION = "3.10"
LAYER_ABI = "cp310"
LAYER_PLATFORM = "manylinux2014_x86_64"
# boto3/botocore (and their own urllib3 dependency) are already provided by
# the Lambda Python runtime itself -- bundling a second copy in the layer
# just bloats it.
LAYER_EXCLUDED_PACKAGES = {"boto3", "botocore", "urllib3"}

def upload():
    uploadLambda()

def upload_layer():
    uploadLambdaLayer()

def deploy_all():
    uploadLambdaLayer()
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
    load_local_env()
    repo_url = os.getenv('GIT_REPO_URL')
    repo_branch = os.getenv('GIT_REPO_BRANCH')
    repo_dir = "/tmp/dompet"
    zip_path = "/tmp/dompet.zip"
    function_name = "dompet"

    subprocess.run(["git", "clone", "--branch", repo_branch, repo_url, repo_dir], check=True)
    _zip_lambda_package(repo_dir, zip_path)

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


def uploadLambdaLayer():
    load_local_env()
    function_name = "dompet"
    build_dir = tempfile.mkdtemp(prefix="dompet-layer-")
    python_dir = os.path.join(build_dir, "python")
    zip_path = os.path.join(build_dir, "layer.zip")

    filtered_requirements = _filtered_layer_requirements(build_dir)

    subprocess.run(
        [
            "pip", "install",
            "--target", python_dir,
            "-r", filtered_requirements,
            "--platform", LAYER_PLATFORM,
            "--python-version", LAYER_PYTHON_VERSION,
            "--implementation", "cp",
            "--abi", LAYER_ABI,
            "--only-binary=:all:",
        ],
        check=True,
    )

    _zip_layer_package(build_dir, zip_path)

    session = boto3.Session(profile_name="dompet-user")
    client = session.client("lambda")
    with open(zip_path, "rb") as fp:
        zip_content = fp.read()

    response = client.publish_layer_version(
        LayerName=LAYER_NAME,
        Content={"ZipFile": zip_content},
        CompatibleRuntimes=[LAYER_RUNTIME],
    )
    layer_version_arn = response["LayerVersionArn"]
    print(f"Published layer version: {layer_version_arn}")

    client.update_function_configuration(
        FunctionName=function_name,
        Layers=[layer_version_arn],
    )
    _wait_for_update(client, function_name)
    print(f"Attached layer to {function_name}")

    shutil.rmtree(build_dir)
    return layer_version_arn


def _filtered_layer_requirements(build_dir: str) -> str:
    filtered_path = os.path.join(build_dir, "layer-requirements.txt")
    with open("requirements.txt") as src, open(filtered_path, "w") as dst:
        for line in src:
            package_name = re.split(r"[=<>!~\[]", line.strip())[0]
            if package_name and package_name.lower() not in LAYER_EXCLUDED_PACKAGES:
                dst.write(line)
    return filtered_path


def _zip_layer_package(build_dir: str, zip_path: str) -> None:
    python_dir = os.path.join(build_dir, "python")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(python_dir):
            for filename in files:
                file_path = os.path.join(root, filename)
                arcname = os.path.relpath(file_path, build_dir)
                zf.write(file_path, arcname=arcname)


def _wait_for_update(client, function_name: str) -> None:
    # Lambda rejects a second config/code update while one is still
    # applying -- matters for `deploy_all`, which calls uploadLambdaLayer()
    # (a config update) immediately followed by uploadLambda() (a code
    # update).
    while True:
        config = client.get_function_configuration(FunctionName=function_name)
        if config["LastUpdateStatus"] != "InProgress":
            return
        time.sleep(2)


def _zip_lambda_package(repo_dir: str, zip_path: str) -> None:
    excludes = {os.path.normpath(p) for p in LAMBDA_ZIP_EXCLUDES}

    def is_excluded(rel_path: str) -> bool:
        return any(
            rel_path == excluded or rel_path.startswith(excluded + os.sep)
            for excluded in excludes
        )

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(repo_dir):
            rel_root = os.path.relpath(root, repo_dir)
            dirs[:] = [
                d for d in dirs
                if not is_excluded(os.path.normpath(os.path.join(rel_root, d)))
            ]
            for filename in files:
                rel_path = os.path.normpath(os.path.join(rel_root, filename))
                if is_excluded(rel_path):
                    continue
                zf.write(os.path.join(root, filename), arcname=rel_path)


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
        upload: pushes code changes to AWS Lambda
        upload-layer: builds and publishes a new Lambda layer version (third-party deps), attaches it to the function
        deploy-all: upload-layer followed by upload
        migrate: create databases
        """,
        add_help=True
    )
    parser.add_argument(
        "--command",
        choices=[
            "upload",
            "upload-layer",
            "deploy-all",
            "migrate"
        ],
        required=True,
        help="Setup commands to run"
    )

    args = parser.parse_args()

    if args.command == "upload":
        upload()
    if args.command == "upload-layer":
        upload_layer()
    if args.command == "deploy-all":
        deploy_all()
    if args.command == "migrate":
        migrate()