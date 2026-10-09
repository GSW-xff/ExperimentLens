#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f dist/index.html ]]; then
  ./node_modules/.bin/tsc -b
  ./node_modules/.bin/vite build
fi
alembic upgrade head

experimentlens-worker &
WORKER_PID=$!
experimentlens-api &
API_PID=$!

cleanup() {
  kill "$API_PID" "$WORKER_PID" 2>/dev/null || true
  wait "$API_PID" "$WORKER_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "ExperimentLens: http://127.0.0.1:${EXPERIMENTLENS_PORT:-5050}"
echo "API PID=$API_PID, Worker PID=$WORKER_PID"
while kill -0 "$API_PID" 2>/dev/null && kill -0 "$WORKER_PID" 2>/dev/null; do
  sleep 1
done
