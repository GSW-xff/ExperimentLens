import time

import pytest
from experimentlens.agent.orchestrator import AgentOrchestrator
from experimentlens.agent.worker import AgentWorker
from experimentlens.persistence import Database, SQLAgentRunRepository
from experimentlens.persistence.models import EvidenceRefRecord, ToolCallRecord
from experimentlens.repositories.local import LocalRepository
from experimentlens.service import ExperimentService
from sqlalchemy import func, select


class SimulatedWorkerCrash(BaseException):
    pass


@pytest.mark.parametrize("crash_point", [
    "model.completed_before_commit",
    "tool.executed_before_commit",
    "evidence.validated_before_commit",
])
def test_worker_recovers_at_persisted_boundaries_without_duplicates(tmp_path, crash_point):
    database = Database(f"sqlite:///{tmp_path / 'control.db'}")
    database.create_schema()
    workspace = LocalRepository(tmp_path / "workspace")
    project = ExperimentService(workspace).create_demo()
    repository = SQLAgentRunRepository(database)
    orchestrator = AgentOrchestrator(
        workspace,
        repository=repository,
        auto_execute=False,
    )
    run = orchestrator.create_run(project.id, "比较实验组", max_steps=5, token_budget=500)
    fired = False

    def crash_once(point, _run):
        nonlocal fired
        if point == crash_point and not fired:
            fired = True
            raise SimulatedWorkerCrash(point)

    first = AgentWorker(
        database,
        workspace,
        owner="worker-before-crash",
        lease_seconds=0.05,
        fault_hook=crash_once,
    )
    with pytest.raises(SimulatedWorkerCrash):
        first.process_run(run.id)
    time.sleep(0.08)

    replacement = AgentWorker(
        database,
        workspace,
        owner="worker-after-crash",
        lease_seconds=0.2,
    )
    assert replacement.process_run(run.id) == run.id
    completed = repository.get(run.id)

    assert completed.status.value == "completed"
    assert completed.used_tokens == 72
    assert len(completed.tool_calls) == 2
    assert all(call.status.value == "completed" for call in completed.tool_calls)
    calls = repository.list_tool_calls(run.id)
    assert len(calls) == len({call["idempotency_key"] for call in calls}) == 2
    events = repository.list_events(run.id)
    assert [event.id for event in events] == list(range(1, len(events) + 1))
    assert sum(event.type == "agent.completed" for event in events) == 1
    with database.session() as session:
        evidence_count = session.scalar(select(func.count()).select_from(
            EvidenceRefRecord
        ).where(EvidenceRefRecord.agent_run_id == run.id))
        tool_count = session.scalar(select(func.count()).select_from(
            ToolCallRecord
        ).where(ToolCallRecord.agent_run_id == run.id))
    assert evidence_count == len(completed.evidence_refs)
    assert tool_count == 2


def test_fencing_token_prevents_two_workers_from_claiming_same_run(tmp_path):
    database = Database(f"sqlite:///{tmp_path / 'control.db'}")
    database.create_schema()
    workspace = LocalRepository(tmp_path / "workspace")
    project = ExperimentService(workspace).create_demo()
    repository = SQLAgentRunRepository(database)
    run = AgentOrchestrator(
        workspace, repository=repository, auto_execute=False
    ).create_run(project.id, "比较实验组")

    first = repository.claim_run(run.id, "worker-a", lease_seconds=10)
    second = repository.claim_run(run.id, "worker-b", lease_seconds=10)

    assert first is not None
    assert second is None
    assert repository.owns_lease(run.id, "worker-a", first[1]) is True
    assert repository.owns_lease(run.id, "worker-a", first[1] + 1) is False
