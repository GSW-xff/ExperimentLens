from __future__ import annotations

import json

from flask import Blueprint, Response, current_app, jsonify, request, stream_with_context

from ..agent.orchestrator import TERMINAL_STATUSES, AgentOrchestrator

agent_runs_api = Blueprint("agent_runs_api", __name__)


def _orchestrator() -> AgentOrchestrator:
    return current_app.extensions["experimentlens_agent_orchestrator"]


@agent_runs_api.post("/projects/<project_id>/agent-runs")
def create_agent_run(project_id: str):
    payload = request.get_json(silent=True) or {}
    run = _orchestrator().create_run(
        project_id,
        payload.get("question", ""),
        max_steps=int(payload.get("max_steps", 8)),
        token_budget=int(payload.get("token_budget", 8000)),
    )
    return jsonify(run.model_dump(mode="json")), 202


@agent_runs_api.get("/agent-runs/<agent_run_id>")
def get_agent_run(agent_run_id: str):
    return jsonify(_orchestrator().get_run(agent_run_id).model_dump(mode="json"))


@agent_runs_api.get("/agent-runs/<agent_run_id>/events")
def get_agent_run_events(agent_run_id: str):
    after_id = int(request.args.get("after", 0))
    events = _orchestrator().repository.list_events(agent_run_id, after_id)
    return jsonify([event.model_dump(mode="json") for event in events])


@agent_runs_api.get("/agent-runs/<agent_run_id>/stream")
def stream_agent_run(agent_run_id: str):
    header_id = request.headers.get("Last-Event-ID")
    after_id = int(header_id or request.args.get("after", 0))
    orchestrator = _orchestrator()
    orchestrator.get_run(agent_run_id)

    @stream_with_context
    def generate():
        cursor = after_id
        while True:
            events = orchestrator.repository.wait_for_events(agent_run_id, cursor, 5.0)
            if events:
                for event in events:
                    cursor = event.id
                    payload = json.dumps(event.model_dump(mode="json"), ensure_ascii=False)
                    yield f"id: {event.id}\nevent: {event.type}\ndata: {payload}\n\n"
            else:
                yield ": heartbeat\n\n"
            run = orchestrator.get_run(agent_run_id)
            if run.status in TERMINAL_STATUSES and not orchestrator.repository.list_events(
                agent_run_id, cursor
            ):
                break

    response = Response(generate(), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response


@agent_runs_api.post("/agent-runs/<agent_run_id>/cancel")
def cancel_agent_run(agent_run_id: str):
    return jsonify(_orchestrator().cancel(agent_run_id).model_dump(mode="json"))


@agent_runs_api.post("/agent-runs/<agent_run_id>/retry")
def retry_agent_run(agent_run_id: str):
    run = _orchestrator().retry(agent_run_id)
    return jsonify(run.model_dump(mode="json")), 202
