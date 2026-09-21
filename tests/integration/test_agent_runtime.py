import time

from experimentlens.agent import MockModelGateway
from experimentlens.agent.model_gateway import OpenAIModelGateway
from experimentlens.agent.orchestrator import AgentOrchestrator
from experimentlens.app import create_app


def _wait_for_terminal(client, agent_run_id: str):
    for _ in range(100):
        payload = client.get(f"/api/agent-runs/{agent_run_id}").get_json()
        if payload["status"] in {"completed", "failed", "cancelled", "budget_exhausted"}:
            return payload
        time.sleep(0.01)
    raise AssertionError("agent run did not finish")


def test_agent_calls_multiple_tools_persists_events_and_streams_sse(tmp_path):
    app = create_app({"TESTING": True, "WORKSPACE_ROOT": tmp_path / "workspace"})
    client = app.test_client()
    project = client.post("/api/projects/demo").get_json()
    gateway = MockModelGateway([
        {
            "content": "",
            "tool_calls": [{"id": "tc-list", "name": "list_runs", "arguments": {"limit": 5}}],
            "input_tokens": 10,
            "output_tokens": 5,
            "finish_reason": "tool_call",
        },
        {
            "content": "",
            "tool_calls": [{"id": "tc-compare", "name": "compare_groups", "arguments": {}}],
            "input_tokens": 20,
            "output_tokens": 5,
            "finish_reason": "tool_call",
        },
        {"content": "候选组整体更好，但需要结合异常运行判断。", "input_tokens": 30, "output_tokens": 12},
    ])
    app.extensions["experimentlens_agent_orchestrator"] = AgentOrchestrator(
        app.extensions["experimentlens_workspace"], gateway
    )

    created = client.post(
        f"/api/projects/{project['id']}/agent-runs",
        json={"question": "比较各组并解释风险", "max_steps": 5, "token_budget": 500},
    )
    assert created.status_code == 202
    agent_run_id = created.get_json()["id"]
    completed = _wait_for_terminal(client, agent_run_id)

    assert completed["status"] == "completed"
    assert completed["step_count"] == 3
    assert [call["tool_name"] for call in completed["tool_calls"]] == [
        "list_runs",
        "compare_groups",
    ]
    assert completed["evidence_refs"]
    events = client.get(f"/api/agent-runs/{agent_run_id}/events").get_json()
    assert [event["id"] for event in events] == list(range(1, len(events) + 1))
    assert {"tool.started", "tool.completed", "evidence.validated", "agent.completed"} <= {
        event["type"] for event in events
    }

    resumed = client.get(
        f"/api/agent-runs/{agent_run_id}/stream",
        headers={"Last-Event-ID": str(events[-2]["id"])},
    )
    body = resumed.get_data(as_text=True)
    assert resumed.mimetype == "text/event-stream"
    assert f"id: {events[-1]['id']}" in body
    assert "event: agent.completed" in body


def test_default_gateway_runs_offline_without_api_key(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app({"TESTING": True, "WORKSPACE_ROOT": tmp_path / "workspace"})
    client = app.test_client()
    project = client.post("/api/projects/demo").get_json()
    response = client.post(
        f"/api/projects/{project['id']}/agent-runs", json={"question": "对比实验组"}
    )
    completed = _wait_for_terminal(client, response.get_json()["id"])
    assert completed["status"] == "completed"
    assert completed["model"] == "deterministic-fallback"
    assert len(completed["tool_calls"]) == 2


def test_openai_responses_payload_parser_extracts_tools_text_and_usage():
    payload = {
        "status": "completed",
        "output": [
            {"type": "function_call", "call_id": "call-1", "name": "list_runs", "arguments": "{\"limit\": 3}"},
            {"type": "message", "content": [{"type": "output_text", "text": "done"}]},
        ],
        "usage": {"input_tokens": 11, "output_tokens": 7},
    }
    response = OpenAIModelGateway._parse(payload)
    assert response.content == "done"
    assert response.tool_calls == [
        {"id": "call-1", "name": "list_runs", "arguments": {"limit": 3}}
    ]
    assert response.input_tokens == 11
    assert response.output_tokens == 7


def test_agent_stops_when_model_exceeds_token_budget(tmp_path):
    app = create_app({"TESTING": True, "WORKSPACE_ROOT": tmp_path / "workspace"})
    client = app.test_client()
    project = client.post("/api/projects/demo").get_json()
    gateway = MockModelGateway([
        {"content": "too expensive", "input_tokens": 80, "output_tokens": 30}
    ])
    app.extensions["experimentlens_agent_orchestrator"] = AgentOrchestrator(
        app.extensions["experimentlens_workspace"], gateway
    )
    created = client.post(
        f"/api/projects/{project['id']}/agent-runs",
        json={"question": "analyze", "token_budget": 100},
    )
    completed = _wait_for_terminal(client, created.get_json()["id"])
    assert completed["status"] == "budget_exhausted"
    assert completed["answer"] is None
