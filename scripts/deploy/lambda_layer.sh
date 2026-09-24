#!/usr/bin/env bash
# Build and publish a new version of the "dompet-layer" Lambda layer
# (third-party deps: pydantic, psycopg2-binary, python-dotenv -- NOT boto3,
# which the Lambda Python runtime already provides), and attach it to the
# "dompet" function, via Setup.py's uploadLambdaLayer().
#
# Requires AWS credentials configured for the "dompet-user" profile, and
# `pip` available on PATH. Builds portably (--platform/--python-version/--abi
# flags target the deployed runtime, python3.10 manylinux x86_64) regardless
# of what machine runs this script.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/../.."

python3 Setup.py --command upload-layer
