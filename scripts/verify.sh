#!/usr/bin/env bash
set -euo pipefail

command -v experimentlens-api >/dev/null
command -v experimentlens-worker >/dev/null
command -v experimentlens-eval >/dev/null

pytest --cov=experimentlens --cov-report=term-missing --cov-fail-under=85
ruff check .
./node_modules/.bin/vitest run
./node_modules/.bin/tsc -b --pretty false
./node_modules/.bin/vite build

VERIFY_DB="$(mktemp /tmp/experimentlens-migration.XXXXXX.db)"
trap 'rm -f "$VERIFY_DB"' EXIT
EXPERIMENTLENS_DATABASE_URL="sqlite:///$VERIFY_DB" alembic upgrade head
EXPERIMENTLENS_DATABASE_URL="sqlite:///$VERIFY_DB" alembic downgrade base
EXPERIMENTLENS_DATABASE_URL="sqlite:///$VERIFY_DB" alembic upgrade head
