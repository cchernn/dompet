#!/usr/bin/env bash
# Build and run dompet locally via Docker + FastAPI (uvicorn).
# Requires a .env at the repo root (see README for DB_POSTGRESQL_* vars).
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/../.."

docker compose up --build "$@"
