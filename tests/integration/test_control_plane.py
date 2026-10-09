import time

from experimentlens.agent.worker import AgentWorker
from experimentlens.control_plane import create_app
from experimentlens.evaluation import load_dataset
from fastapi.testclient import TestClient


def _wait_for_terminal(client: TestClient, run_id: str) -> dict:
    for _ in range(200):
        response = client.get(f"/api/v2/agent-runs/{run_id}")
        payload = response.json()
        if payload["status"] in {"completed", "failed", "cancelled", "budget_exhausted"}:
            return payload
        time.sleep(0.01)
    raise AssertionError("agent run did not finish")


def test_fastapi_control_plane_preserves_legacy_api_and_exposes_durable_runtime(tmp_path):
    app = create_app({
        "TESTING": True,
        "RECOVER_RUNS": False,
        "WORKSPACE_ROOT": tmp_path / "workspace",
        "DATABASE_URL": f"sqlite:///{tmp_path / 'control.db'}",
        "FRONTEND_DIST": tmp_path / "dist",
    })
    with TestClient(app) as client:
        assert client.get("/api/v2/health/live").json()["version"] == "2.0.0"
        assert client.get("/api/v2/health/ready").json()["database"] == "ok"

        legacy_project = client.post("/api/projects/demo")
        assert legacy_project.status_code == 201
        project_id = legacy_project.json()["id"]

        created = client.post(
            f"/api/v2/projects/{project_id}/agent-runs",
            json={"question": "比较实验组", "max_steps": 5, "token_budget": 500},
        )
        assert created.status_code == 202
        assert created.json()["status"] == "pending"
        worker = AgentWorker(app.state.database, app.state.workspace, owner="control-test")
        assert worker.process_run(created.json()["id"]) == created.json()["id"]
        completed = _wait_for_terminal(client, created.json()["id"])
        assert completed["status"] == "completed"
        assert completed["trace_id"]

        events = client.get(f"/api/v2/agent-runs/{completed['id']}/events").json()
        assert [event["id"] for event in events] == list(range(1, len(events) + 1))
        assert "agent.completed" in {event["type"] for event in events}

        trace = client.get(f"/api/v2/traces/{completed['trace_id']}")
        assert trace.status_code == 200
        names = {span["name"] for span in trace.json()["spans"]}
        assert {"agent.run", "model.complete", "tool.execute", "evidence.validate"} <= names

        metrics = client.get("/api/v2/metrics")
        assert metrics.status_code == 200
        assert "agent_runs_total" in metrics.text
        assert "tool_calls_total" in metrics.text

        dataset = client.get("/api/v2/evaluations/dataset").json()
        assert dataset["case_count"] >= 20
        _, cases = load_dataset(__import__("pathlib").Path(__file__).parents[2] / "evals/cases/golden-v2.jsonl")
        assert len(cases) == 30
        forged = client.post(
            "/api/v2/evaluations/run",
            json={"trajectories": [{"case_id": "forged", "tools": []}]},
        )
        assert forged.status_code == 422
        evaluated = client.post(
            "/api/v2/evaluations/run",
            json={"dataset_version": "2.0.0", "candidate_model": "deterministic-evaluation"},
        )
        assert evaluated.status_code == 200
        assert evaluated.json()["gate_passed"] is True
        assert evaluated.json()["case_count"] == 30
        assert evaluated.json()["versions"]["git_commit"]
        latest = client.get("/api/v2/evaluations/latest").json()
        assert latest["id"] == evaluated.json()["id"]


def test_control_plane_rejects_scope_and_budget_injection(tmp_path):
    app = create_app({
        "TESTING": True,
        "RECOVER_RUNS": False,
        "WORKSPACE_ROOT": tmp_path / "workspace",
        "DATABASE_URL": f"sqlite:///{tmp_path / 'control.db'}",
    })
    with TestClient(app) as client:
        project_id = client.post("/api/projects/demo").json()["id"]
        response = client.post(
            f"/api/v2/projects/{project_id}/agent-runs",
            json={"question": "analyze", "project_id": "other", "token_budget": 1},
        )
        assert response.status_code == 422
