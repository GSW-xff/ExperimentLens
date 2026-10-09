#!/usr/bin/env bash
set -euo pipefail

DEMO_ROOT="${EXPERIMENTLENS_DEMO_ROOT:-.experimentlens/interview-demo}"
export EXPERIMENTLENS_WORKSPACE="$DEMO_ROOT/workspace"
export EXPERIMENTLENS_DATABASE_URL="sqlite:///$DEMO_ROOT/control-plane.db"
export EXPERIMENTLENS_EVALUATION_WORKSPACE="$DEMO_ROOT/evaluation-workspace"
export EXPERIMENTLENS_EVALUATION_DATABASE_URL="sqlite:///$DEMO_ROOT/evaluation.db"

mkdir -p "$DEMO_ROOT"
alembic upgrade head
./node_modules/.bin/tsc -b
./node_modules/.bin/vite build
experimentlens-api >"$DEMO_ROOT/api.log" 2>&1 &
API_PID=$!
experimentlens-worker >"$DEMO_ROOT/worker-1.log" 2>&1 &
WORKER_PID=$!

cleanup() {
  kill "$API_PID" "$WORKER_PID" 2>/dev/null || true
  wait "$API_PID" "$WORKER_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

for _ in $(seq 1 50); do
  if curl --silent --fail http://127.0.0.1:5050/api/v2/health/ready >/dev/null; then
    break
  fi
  sleep 0.1
done

PROJECT_JSON="$(curl --silent --fail -X POST http://127.0.0.1:5050/api/projects/demo)"
PROJECT_ID="$(python -c 'import json,sys; print(json.loads(sys.argv[1])["id"])' "$PROJECT_JSON")"
RUN_JSON="$(curl --silent --fail -H 'Content-Type: application/json' -d '{"question":"列出运行并比较实验组","max_steps":5,"token_budget":500}' "http://127.0.0.1:5050/api/v2/projects/$PROJECT_ID/agent-runs")"
RUN_ID="$(python -c 'import json,sys; print(json.loads(sys.argv[1])["id"])' "$RUN_JSON")"

kill "$WORKER_PID" 2>/dev/null || true
wait "$WORKER_PID" 2>/dev/null || true
sleep 1
experimentlens-worker >"$DEMO_ROOT/worker-2.log" 2>&1 &
WORKER_PID=$!

for _ in $(seq 1 100); do
  RUN_JSON="$(curl --silent --fail "http://127.0.0.1:5050/api/v2/agent-runs/$RUN_ID")"
  STATUS="$(python -c 'import json,sys; print(json.loads(sys.argv[1])["status"])' "$RUN_JSON")"
  if [[ "$STATUS" =~ ^(completed|failed|cancelled|budget_exhausted)$ ]]; then
    break
  fi
  sleep 0.1
done

TRACE_ID="$(python -c 'import json,sys; print(json.loads(sys.argv[1])["trace_id"])' "$RUN_JSON")"
curl --silent --fail "http://127.0.0.1:5050/api/v2/agent-runs/$RUN_ID/events" >"$DEMO_ROOT/events.json"
curl --silent --fail "http://127.0.0.1:5050/api/v2/traces/$TRACE_ID" >"$DEMO_ROOT/trace.json"
experimentlens-eval --output "$DEMO_ROOT/evaluation.json" --markdown-output "$DEMO_ROOT/evaluation.md"
experimentlens-benchmark --runs 100 --workers 2 \
  --workspace "$DEMO_ROOT/reliability-workspace" \
  --database-url "sqlite:///$DEMO_ROOT/reliability.db" \
  --output "$DEMO_ROOT/reliability.json" \
  --markdown-output "$DEMO_ROOT/reliability.md"

echo "Demo completed: $DEMO_ROOT"
echo "AgentRun: $RUN_ID ($STATUS), Trace: $TRACE_ID"
