from __future__ import annotations

import argparse
import json
import platform
import resource
import statistics
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from .agent.orchestrator import TERMINAL_STATUSES, AgentOrchestrator
from .agent.worker import AgentWorker
from .persistence import Database, SQLAgentRunRepository
from .repositories.local import LocalRepository
from .service import ExperimentService


class InjectedWorkerCrash(BaseException):
    """A hard-stop failpoint used by the reproducible reliability experiment."""


def run_reliability_experiment(
    *,
    run_count: int = 100,
    worker_count: int = 2,
    workspace_root: str | Path = ".experimentlens/reliability/workspace",
    database_url: str | None = None,
) -> dict[str, Any]:
    if run_count < 1 or worker_count < 2:
        raise ValueError("reliability experiment requires at least one run and two workers")
    root = Path(workspace_root)
    url = database_url or f"sqlite:///{root.parent / 'reliability.db'}"
    database = Database(url)
    database.create_schema()
    workspace = LocalRepository(root)
    project = ExperimentService(workspace).create_demo()
    repository = SQLAgentRunRepository(database)
    orchestrator = AgentOrchestrator(
        workspace,
        repository=repository,
        auto_execute=False,
    )
    runs = [
        orchestrator.create_run(
            project.id,
            f"可靠性基线 #{index}: 列出运行并比较实验组",
            max_steps=5,
            token_budget=500,
        )
        for index in range(run_count)
    ]
    crashed_run: dict[str, str | float | None] = {
        "id": None,
        "crashed_at": None,
    }
    crash_lock = threading.Lock()

    def crash_once(point, run):
        if point != "tool.executed_before_commit":
            return
        with crash_lock:
            if crashed_run["id"] is None:
                crashed_run["id"] = run.id
                crashed_run["crashed_at"] = time.time()
                raise InjectedWorkerCrash(run.id)

    stop_events = [threading.Event() for _ in range(worker_count)]
    workers = [
        AgentWorker(
            database,
            workspace,
            owner=f"benchmark-worker-{index}",
            lease_seconds=0.2,
            poll_seconds=0.01,
            fault_hook=crash_once if index == 0 else None,
        )
        for index in range(worker_count)
    ]
    crashes: list[str] = []

    def run_worker(index: int) -> None:
        try:
            workers[index].run_forever(stop_events[index])
        except InjectedWorkerCrash as error:
            crashes.append(str(error))

    started_wall = time.time()
    started_cpu = time.process_time()
    threads = [
        threading.Thread(target=run_worker, args=(index,), daemon=True)
        for index in range(worker_count)
    ]
    for thread in threads:
        thread.start()
    deadline = time.monotonic() + max(30.0, run_count * 2.0)
    while time.monotonic() < deadline:
        current = [repository.get(run.id) for run in runs]
        if all(run.status in TERMINAL_STATUSES for run in current):
            break
        time.sleep(0.02)
    else:
        raise TimeoutError("reliability experiment did not reach terminal states")
    for stop in stop_events:
        stop.set()
    for thread in threads:
        thread.join(timeout=2)

    completed = [repository.get(run.id) for run in runs]
    tool_calls = [
        call for run in completed for call in repository.list_tool_calls(run.id)
    ]
    idempotency_keys = [str(call["idempotency_key"]) for call in tool_calls]
    lost_events = 0
    sse_replay_failures = 0
    queue_waits = []
    durations = []
    for run in completed:
        events = repository.list_events(run.id)
        sequences = [event.id for event in events]
        lost_events += len(set(range(1, len(events) + 1)) - set(sequences))
        midpoint = len(events) // 2
        first_delivery = events[:midpoint]
        cursor = first_delivery[-1].id if first_delivery else 0
        replay = repository.list_events(run.id, cursor)
        if [event.id for event in [*first_delivery, *replay]] != sequences:
            sse_replay_failures += 1
        started_event = next(event for event in events if event.type == "agent.started")
        queue_waits.append(_milliseconds(run.created_at, started_event.created_at))
        durations.append(_milliseconds(run.started_at or run.created_at, run.completed_at))

    crashed_id = str(crashed_run["id"] or "")
    crashed_completed = next((run for run in completed if run.id == crashed_id), None)
    recovery_ms = 0.0
    if crashed_completed and crashed_run["crashed_at"] and crashed_completed.completed_at:
        recovery_ms = max(
            0.0,
            datetime.fromisoformat(crashed_completed.completed_at).timestamp()
            - float(crashed_run["crashed_at"]),
        ) * 1000
    usage = resource.getrusage(resource.RUSAGE_SELF)
    max_rss_kib = usage.ru_maxrss / 1024 if platform.system() == "Darwin" else usage.ru_maxrss
    terminal_success = sum(run.status.value == "completed" for run in completed)
    report = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "configuration": {
            "run_count": run_count,
            "worker_count": worker_count,
            "database": "sqlite" if url.startswith("sqlite") else "postgresql",
            "offline_model": "deterministic-fallback",
            "tool_calls_per_run": "2",
        },
        "results": {
            "completion_rate": terminal_success / run_count,
            "duplicate_tool_calls": len(idempotency_keys) - len(set(idempotency_keys)),
            "lost_events": lost_events,
            "sse_replay_failures": sse_replay_failures,
            "queue_wait_ms_p50": _percentile(queue_waits, 0.50),
            "queue_wait_ms_p95": _percentile(queue_waits, 0.95),
            "agent_duration_ms_p50": _percentile(durations, 0.50),
            "agent_duration_ms_p95": _percentile(durations, 0.95),
            "crash_recovery_ms": recovery_ms,
            "worker_crashes_injected": len(crashes),
            "wall_time_seconds": time.time() - started_wall,
            "process_cpu_seconds": time.process_time() - started_cpu,
            "process_max_rss_kib": max_rss_kib,
            "database_pool_checked_out": database.engine.pool.checkedout(),
        },
        "limitations": [
            "This is a local SQLite baseline, not an internet-production SLO.",
            "CPU and RSS describe the combined benchmark process, not a database server.",
        ],
    }
    return report


def render_reliability_markdown(report: dict[str, Any]) -> str:
    config = report["configuration"]
    results = report["results"]
    lines = [
        "# ExperimentLens Reliability Baseline",
        "",
        f"Generated: {report['generated_at']}",
        "",
        "## Configuration",
        "",
        *[f"- {key}: `{value}`" for key, value in config.items()],
        "",
        "## Results",
        "",
        *[f"- {key}: `{value}`" for key, value in results.items()],
        "",
        "## Limitations",
        "",
        *[f"- {item}" for item in report["limitations"]],
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Agent worker reliability baseline")
    parser.add_argument("--runs", type=int, default=100)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--workspace", default=".experimentlens/reliability/workspace")
    parser.add_argument("--database-url")
    parser.add_argument("--output", default="docs/evidence/reliability-baseline.json")
    parser.add_argument("--markdown-output", default="docs/evidence/reliability-baseline.md")
    args = parser.parse_args()
    report = run_reliability_experiment(
        run_count=args.runs,
        worker_count=args.workers,
        workspace_root=args.workspace,
        database_url=args.database_url,
    )
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown = Path(args.markdown_output)
    markdown.parent.mkdir(parents=True, exist_ok=True)
    markdown.write_text(render_reliability_markdown(report), encoding="utf-8")


def _milliseconds(start: str, end: str | None) -> float:
    if not end:
        return 0.0
    return max(
        0.0,
        (datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds() * 1000,
    )


def _percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    return statistics.quantiles(values, n=100, method="inclusive")[
        max(0, min(99, int(quantile * 100) - 1))
    ]


if __name__ == "__main__":
    main()
