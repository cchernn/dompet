#!/usr/bin/env bash
# Deploy to AWS Lambda via Setup.py's uploadLambda(), which clones
# GIT_REPO_URL@GIT_REPO_BRANCH fresh and pushes it as the function code for
# the "dompet" Lambda function under the "dompet-user" AWS profile.
#
# Required: GIT_REPO_URL and GIT_REPO_BRANCH, either already exported in
# the shell or present in .env -- uploadLambda() loads .env itself, so no
# shell-level check is done here (a hard require at this point would block
# the common case of setting them only in .env).
# Requires AWS credentials configured for the "dompet-user" profile.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/../.."

python3 Setup.py --command upload
