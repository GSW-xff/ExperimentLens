from __future__ import annotations

import asyncio
import json
import os
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from a2wsgi import WSGIMiddleware
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from .agent.orchestrator import TERMINAL_STATUSES, AgentOrchestrator
from .app import create_app as create_legacy_app
from .evaluation import load_dataset
from .evaluation.executor import EvaluationExecutor
from .observability import PlatformMetrics
from .persistence import Database, SQLAgentRunRepository
from .repositories.local import LocalRepository


class CreateAgentRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=4000)
    max_steps: int | None = Field(default=None, ge=1, le=50)
    token_budget: int | None = Field(default=None, ge=128, le=1_000_000)


class RunEvaluationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_version: str = "2.0.0"
    candidate_model: str = "deterministic-evaluation"
    max_steps: int = Field(default=8, ge=1, le=50)
    token_budget: int = Field(default=8000, ge=128, le=1_000_000)
    compare_to_latest: bool = False


def create_app(config: dict | None = None) -> FastAPI:
    settings = config or {}
    workspace_root = Path(settings.get("WORKSPACE_ROOT") or os.environ.get(
        "EXPERIMENTLENS_WORKSPACE", ".experimentlens/workspace"
    ))
    database = Database(settings.get("DATABASE_URL"))
    if settings.get("AUTO_CREATE_SCHEMA", database.url.startswith("sqlite")):
        database.create_schema()
    workspace = LocalRepository(workspace_root)
    metrics = PlatformMetrics()
    agent_repository = SQLAgentRunRepository(database)
    dataset_path = Path(settings.get("EVALUATION_DATASET") or (
        Path(__file__).parents[2] / "evals/cases/golden-v2.jsonl"
    ))
    dataset_hash, evaluation_cases = load_dataset(dataset_path)
    orchestrator = AgentOrchestrator(
        workspace,
        repository=agent_repository,
        metrics=metrics,
        auto_execute=False,
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        # Agent execution belongs to experimentlens-worker. Expired leases are
        # reclaimed by workers, so an API restart never executes queued work.
        yield

    app = FastAPI(
        title="ExperimentLens Control Plane",
        version="2.0.0",
        description="Durable, evidence-first experiment diagnosis control plane",
        lifespan=lifespan,
    )
    app.state.database = database
    app.state.workspace = workspace
    app.state.metrics = metrics
    app.state.orchestrator = orchestrator
    app.state.agent_repository = agent_repository

    @app.middleware("http")
    async def observe_http(request: Request, call_next):
        started = time.perf_counter()
        response = await call_next(request)
        route = request.scope.get("route")
        route_path = getattr(route, "path", "unmatched")
        metrics.http_requests.labels(request.method, route_path, str(response.status_code)).inc()
        metrics.http_duration.labels(request.method, route_path).observe(time.perf_counter() - started)
        return response

    @app.exception_handler(FileNotFoundError)
    async def missing_handler(_request: Request, error: FileNotFoundError):
        return JSONResponse({"error": f"resource not found: {error}"}, status_code=404)

    @app.exception_handler(ValueError)
    async def validation_handler(_request: Request, error: ValueError):
        return JSONResponse({"error": str(error)}, status_code=400)

    @app.get("/api/v2/health/live", tags=["platform"])
    async def live():
        return {"status": "ok", "service": "experimentlens-control-plane", "version": "2.0.0"}

    @app.get("/api/v2/health/ready", tags=["platform"])
    async def ready():
        if not database.ready():
            raise HTTPException(status_code=503, detail="database unavailable")
        return {"status": "ready", "database": "ok"}

    @app.get("/api/v2/metrics", include_in_schema=False)
    async def prometheus_metrics():
        return Response(metrics.render(), media_type="text/plain; version=0.0.4")

    @app.post("/api/v2/projects/{project_id}/agent-runs", status_code=202, tags=["agent"])
    async def create_agent_run(project_id: str, payload: CreateAgentRunRequest):
        run = orchestrator.create_run(
            project_id,
            payload.question,
            max_steps=payload.max_steps,
            token_budget=payload.token_budget,
        )
        return run.model_dump(mode="json")

    @app.get("/api/v2/agent-runs/{agent_run_id}", tags=["agent"])
    async def get_agent_run(agent_run_id: str):
        return orchestrator.get_run(agent_run_id).model_dump(mode="json")

    @app.get("/api/v2/agent-runs/{agent_run_id}/events", tags=["agent"])
    async def get_agent_events(agent_run_id: str, after: int = 0):
        return [
            event.model_dump(mode="json")
            for event in agent_repository.list_events(agent_run_id, after)
        ]

    @app.get("/api/v2/agent-runs/{agent_run_id}/stream", tags=["agent"])
    async def stream_agent_events(request: Request, agent_run_id: str, after: int = 0):
        header = request.headers.get("last-event-id")
        cursor = int(header or after)
        orchestrator.get_run(agent_run_id)
        if cursor:
            metrics.sse_reconnects.inc()

        async def stream():
            nonlocal cursor
            metrics.sse_connections.inc()
            try:
                while True:
                    events = await asyncio.to_thread(
                        agent_repository.wait_for_events, agent_run_id, cursor, 5.0
                    )
                    if events:
                        for event in events:
                            cursor = event.id
                            encoded = json.dumps(event.model_dump(mode="json"), ensure_ascii=False)
                            yield f"id: {event.id}\nevent: {event.type}\ndata: {encoded}\n\n"
                    else:
                        yield ": heartbeat\n\n"
                    run = orchestrator.get_run(agent_run_id)
                    if run.status in TERMINAL_STATUSES and not agent_repository.list_events(
                        agent_run_id, cursor
                    ):
                        break
            finally:
                metrics.sse_connections.dec()

        return StreamingResponse(stream(), media_type="text/event-stream", headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        })

    @app.post("/api/v2/agent-runs/{agent_run_id}/cancel", tags=["agent"])
    async def cancel_agent_run(agent_run_id: str):
        return orchestrator.cancel(agent_run_id).model_dump(mode="json")

    @app.post("/api/v2/agent-runs/{agent_run_id}/retry", status_code=202, tags=["agent"])
    async def retry_agent_run(agent_run_id: str):
        return orchestrator.retry(agent_run_id).model_dump(mode="json")

    @app.get("/api/v2/traces/{trace_id}", tags=["observability"])
    async def get_trace(trace_id: str):
        spans = agent_repository.list_spans(trace_id)
        if not spans:
            raise FileNotFoundError(trace_id)
        return {"trace_id": trace_id, "spans": [span.model_dump(mode="json") for span in spans]}

    @app.get("/api/v2/evaluations/dataset", tags=["evaluation"])
    async def get_evaluation_dataset():
        tag_counts: dict[str, int] = {}
        for case in evaluation_cases:
            for tag in case.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        return {
            "version": "2.0.0",
            "hash": dataset_hash,
            "case_count": len(evaluation_cases),
            "tag_counts": tag_counts,
        }

    @app.post("/api/v2/evaluations/run", tags=["evaluation"])
    async def run_evaluation(payload: RunEvaluationRequest):
        if payload.dataset_version != "2.0.0":
            raise ValueError(f"unknown dataset version: {payload.dataset_version}")
        latest = agent_repository.latest_evaluation() if payload.compare_to_latest else None
        executor = EvaluationExecutor(
            workspace,
            database,
            cases=evaluation_cases,
            dataset_hash=dataset_hash,
            model=payload.candidate_model,
            max_steps=payload.max_steps,
            token_budget=payload.token_budget,
        )
        report = await asyncio.to_thread(
            executor.execute,
            latest[1] if latest else None,
        )
        saved = agent_repository.latest_evaluation()
        return {
            "id": saved[0] if saved else None,
            **report.model_dump(mode="json"),
        }

    @app.get("/api/v2/evaluations/latest", tags=["evaluation"])
    async def get_latest_evaluation():
        latest = agent_repository.latest_evaluation()
        if latest is None:
            return {"status": "not_run"}
        evaluation_run_id, report = latest
        return {"id": evaluation_run_id, "status": "complete", **report.model_dump(mode="json")}

    legacy = create_legacy_app({
        "WORKSPACE_INSTANCE": workspace,
        "AGENT_ORCHESTRATOR_INSTANCE": orchestrator,
        "TESTING": bool(settings.get("TESTING")),
        "FRONTEND_DIST": settings.get("FRONTEND_DIST"),
    })
    app.mount("/", WSGIMiddleware(legacy))
    return app


app = create_app()


def main() -> None:
    uvicorn.run(
        "experimentlens.control_plane:app",
        host=os.environ.get("EXPERIMENTLENS_HOST", "127.0.0.1"),
        port=int(os.environ.get("EXPERIMENTLENS_PORT", "5050")),
        reload=False,
    )


if __name__ == "__main__":
    main()
