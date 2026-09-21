from __future__ import annotations

import json
import threading
from pathlib import Path

from ..domain import AgentEvent, AgentRun
from ..workspace import Workspace


class LocalAgentRunRepository:
    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace
        self._lock = threading.RLock()
        self._condition = threading.Condition(self._lock)

    def create(self, run: AgentRun) -> None:
        directory = self._run_dir(run.project_id, run.id)
        directory.mkdir(parents=True, exist_ok=False)
        self.save(run)
        (directory / "events.jsonl").touch()
        (directory / "tool-calls.jsonl").touch()

    def save(self, run: AgentRun) -> None:
        path = self._run_dir(run.project_id, run.id) / "run.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(run.model_dump_json(indent=2), encoding="utf-8")
        temporary.replace(path)

    def get(self, agent_run_id: str) -> AgentRun:
        path = self._find_run_path(agent_run_id)
        return AgentRun.model_validate_json(path.read_text(encoding="utf-8"))

    def append_event(
        self, agent_run_id: str, event_type: str, payload: dict | None = None
    ) -> AgentEvent:
        with self._condition:
            run = self.get(agent_run_id)
            path = self._run_dir(run.project_id, run.id) / "events.jsonl"
            events = self.list_events(agent_run_id)
            event = AgentEvent(
                id=(events[-1].id + 1) if events else 1,
                agent_run_id=agent_run_id,
                type=event_type,
                payload=payload or {},
            )
            with path.open("a", encoding="utf-8") as handle:
                handle.write(event.model_dump_json() + "\n")
                handle.flush()
            self._condition.notify_all()
            return event

    def append_tool_call(self, agent_run_id: str, payload: dict) -> None:
        with self._lock:
            run = self.get(agent_run_id)
            path = self._run_dir(run.project_id, run.id) / "tool-calls.jsonl"
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def list_events(self, agent_run_id: str, after_id: int = 0) -> list[AgentEvent]:
        run = self.get(agent_run_id)
        path = self._run_dir(run.project_id, run.id) / "events.jsonl"
        if not path.exists():
            return []
        return [
            AgentEvent.model_validate_json(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and json.loads(line)["id"] > after_id
        ]

    def wait_for_events(
        self, agent_run_id: str, after_id: int, timeout_seconds: float
    ) -> list[AgentEvent]:
        with self._condition:
            events = self.list_events(agent_run_id, after_id)
            if events:
                return events
            self._condition.wait(timeout_seconds)
            return self.list_events(agent_run_id, after_id)

    def _run_dir(self, project_id: str, agent_run_id: str) -> Path:
        safe = "".join(character for character in agent_run_id if character.isalnum() or character in "-_")
        if safe != agent_run_id or not safe:
            raise ValueError("invalid agent run id")
        return self.workspace.project_dir(project_id) / "agent-runs" / safe

    def _find_run_path(self, agent_run_id: str) -> Path:
        safe = "".join(character for character in agent_run_id if character.isalnum() or character in "-_")
        if safe != agent_run_id or not safe:
            raise ValueError("invalid agent run id")
        matches = list(self.workspace.root.glob(f"*/agent-runs/{safe}/run.json"))
        if not matches:
            raise FileNotFoundError(agent_run_id)
        if len(matches) > 1:
            raise ValueError("ambiguous agent run id")
        return matches[0]
