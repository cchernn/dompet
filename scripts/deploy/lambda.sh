#!/usr/bin/env bash
# Deploy to AWS Lambda via Setup.py's uploadLambda(), which clones
# GIT_REPO_URL@GIT_REPO_BRANCH fresh and pushes it as the function code for
# the "dompet" Lambda function under the "dompet-user" AWS profile.
#
# Required env vars: GIT_REPO_URL, GIT_REPO_BRANCH.
# Requires AWS credentials configured for the "dompet-user" profile.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/../.."

: "${GIT_REPO_URL:?GIT_REPO_URL must be set}"
: "${GIT_REPO_BRANCH:?GIT_REPO_BRANCH must be set}"

python3 Setup.py --command upload
