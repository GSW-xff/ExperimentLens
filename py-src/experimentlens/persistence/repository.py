from __future__ import annotations

import json
import threading
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, func, or_, select, update

from ..domain import AgentEvent, AgentRun, AgentRunStatus, AgentStep, AgentStepStatus, TraceSpan
from ..evaluation.runner import EvaluationReport, GoldenCase
from .database import Database
from .models import (
    AgentEventRecord,
    AgentRunRecord,
    AgentStepRecord,
    EvaluationDatasetRecord,
    EvaluationResultRecord,
    EvaluationRunRecord,
    EvidenceRefRecord,
    OutboxRecord,
    ToolCallRecord,
    TraceSpanRecord,
)


class SQLAgentRunRepository:
    """Transactional AgentRun store with an event outbox and replay support."""

    def __init__(self, database: Database) -> None:
        self.database = database
        self._lock = threading.RLock()
        self._condition = threading.Condition(self._lock)

    def create(self, run: AgentRun) -> None:
        with self.database.session() as session, session.begin():
            session.add(AgentRunRecord(
                id=run.id,
                organization_id=run.organization_id,
                project_id=run.project_id,
                status=run.status.value,
                trace_id=run.trace_id,
                payload=run.model_dump_json(),
            ))

    def save(self, run: AgentRun) -> None:
        with self.database.session() as session, session.begin():
            record = session.get(AgentRunRecord, run.id)
            if record is None:
                raise FileNotFoundError(run.id)
            record.status = run.status.value
            record.trace_id = run.trace_id
            record.payload = run.model_dump_json()
            record.updated_at = datetime.now(UTC)
            for reference in run.evidence_refs:
                exists = session.scalar(select(EvidenceRefRecord.id).where(
                    EvidenceRefRecord.agent_run_id == run.id,
                    EvidenceRefRecord.kind == reference.kind,
                    EvidenceRefRecord.evidence_id == reference.id,
                ))
                if exists is None:
                    session.add(EvidenceRefRecord(
                        agent_run_id=run.id,
                        evidence_id=reference.id,
                        kind=reference.kind,
                        payload=reference.model_dump_json(),
                    ))

    def get(self, agent_run_id: str) -> AgentRun:
        with self.database.session() as session:
            record = session.get(AgentRunRecord, agent_run_id)
            if record is None:
                raise FileNotFoundError(agent_run_id)
            return AgentRun.model_validate_json(record.payload)

    def append_event(
        self, agent_run_id: str, event_type: str, payload: dict | None = None
    ) -> AgentEvent:
        with self._condition:
            with self.database.session() as session, session.begin():
                run = session.get(AgentRunRecord, agent_run_id)
                if run is None:
                    raise FileNotFoundError(agent_run_id)
                sequence = int(session.scalar(select(func.max(AgentEventRecord.sequence)).where(
                    AgentEventRecord.agent_run_id == agent_run_id
                )) or 0) + 1
                event = AgentEvent(
                    id=sequence,
                    agent_run_id=agent_run_id,
                    type=event_type,
                    payload=payload or {},
                )
                encoded = event.model_dump_json()
                session.add(AgentEventRecord(
                    agent_run_id=agent_run_id,
                    sequence=sequence,
                    event_type=event_type,
                    payload=encoded,
                ))
                session.add(OutboxRecord(
                    aggregate_id=agent_run_id,
                    sequence=sequence,
                    topic=f"agent-events.{run.organization_id}.{run.project_id}",
                    payload=encoded,
                ))
            self._condition.notify_all()
            return event

    def append_tool_call(self, agent_run_id: str, payload: dict) -> None:
        call_id = str(payload["id"])
        idempotency_key = str(payload.get("idempotency_key") or f"{agent_run_id}:{call_id}")
        with self.database.session() as session, session.begin():
            existing = session.scalar(select(ToolCallRecord.id).where(
                ToolCallRecord.idempotency_key == idempotency_key
            ))
            if existing is not None:
                record = session.get(ToolCallRecord, existing)
                if record is not None:
                    record.status = str(payload["status"])
                    record.payload = json.dumps(payload, ensure_ascii=False)
                return
            session.add(ToolCallRecord(
                id=call_id,
                agent_run_id=agent_run_id,
                idempotency_key=idempotency_key,
                tool_name=str(payload["tool_name"]),
                status=str(payload["status"]),
                payload=json.dumps(payload, ensure_ascii=False),
            ))

    def get_tool_call(self, idempotency_key: str) -> dict | None:
        with self.database.session() as session:
            record = session.scalar(select(ToolCallRecord).where(
                ToolCallRecord.idempotency_key == idempotency_key
            ))
            return json.loads(record.payload) if record is not None else None

    def list_tool_calls(self, agent_run_id: str) -> list[dict]:
        with self.database.session() as session:
            records = session.scalars(
                select(ToolCallRecord)
                .where(ToolCallRecord.agent_run_id == agent_run_id)
                .order_by(ToolCallRecord.created_at, ToolCallRecord.id)
            ).all()
            return [json.loads(record.payload) for record in records]

    def save_step(self, step: AgentStep) -> AgentStep:
        with self.database.session() as session, session.begin():
            record = session.scalar(select(AgentStepRecord).where(
                AgentStepRecord.agent_run_id == step.agent_run_id,
                AgentStepRecord.step_index == step.step_index,
            ))
            values = {
                "step_type": step.step_type,
                "input_hash": step.input_hash,
                "output_hash": step.output_hash,
                "status": step.status.value,
                "attempt": step.attempt,
                "payload": step.model_dump_json(),
                "started_at": _parse_time(step.started_at),
                "finished_at": _parse_time(step.finished_at),
                "error_category": step.error_category,
            }
            if record is None:
                session.add(AgentStepRecord(
                    agent_run_id=step.agent_run_id,
                    step_index=step.step_index,
                    **values,
                ))
            else:
                for key, value in values.items():
                    setattr(record, key, value)
        return step

    def get_step(self, agent_run_id: str, step_index: int) -> AgentStep | None:
        with self.database.session() as session:
            record = session.scalar(select(AgentStepRecord).where(
                AgentStepRecord.agent_run_id == agent_run_id,
                AgentStepRecord.step_index == step_index,
            ))
            return AgentStep.model_validate_json(record.payload) if record is not None else None

    def list_steps(self, agent_run_id: str) -> list[AgentStep]:
        with self.database.session() as session:
            records = session.scalars(
                select(AgentStepRecord)
                .where(AgentStepRecord.agent_run_id == agent_run_id)
                .order_by(AgentStepRecord.step_index)
            ).all()
            return [AgentStep.model_validate_json(record.payload) for record in records]

    def claim_next(self, owner: str, lease_seconds: float = 15.0) -> tuple[AgentRun, int] | None:
        """Atomically claim one queued or expired run and return its fencing token."""
        now = datetime.now(UTC)
        expires = now + timedelta(seconds=lease_seconds)
        terminal = [status.value for status in (
            AgentRunStatus.COMPLETED,
            AgentRunStatus.FAILED,
            AgentRunStatus.CANCELLED,
            AgentRunStatus.BUDGET_EXHAUSTED,
        )]
        with self.database.session() as session, session.begin():
            candidates = session.scalars(
                select(AgentRunRecord)
                .where(
                    AgentRunRecord.status.not_in(terminal),
                    or_(
                        AgentRunRecord.lease_owner.is_(None),
                        AgentRunRecord.lease_expires_at.is_(None),
                        AgentRunRecord.lease_expires_at < now,
                    ),
                )
                .order_by(AgentRunRecord.queued_at, AgentRunRecord.created_at)
                .limit(8)
            ).all()
            for candidate in candidates:
                previous_owner = candidate.lease_owner
                previous_expiry = candidate.lease_expires_at
                predicates = [AgentRunRecord.id == candidate.id]
                if previous_owner is None:
                    predicates.append(AgentRunRecord.lease_owner.is_(None))
                else:
                    predicates.extend([
                        AgentRunRecord.lease_owner == previous_owner,
                        AgentRunRecord.lease_expires_at == previous_expiry,
                    ])
                result = session.execute(
                    update(AgentRunRecord)
                    .where(and_(*predicates))
                    .values(
                        lease_owner=owner,
                        lease_expires_at=expires,
                        heartbeat_at=now,
                        fencing_token=AgentRunRecord.fencing_token + 1,
                    )
                )
                if result.rowcount == 1:
                    session.flush()
                    claimed = session.get(AgentRunRecord, candidate.id)
                    if claimed is None:
                        return None
                    return AgentRun.model_validate_json(claimed.payload), claimed.fencing_token
        return None

    def claim_run(
        self, agent_run_id: str, owner: str, lease_seconds: float = 15.0
    ) -> tuple[AgentRun, int] | None:
        now = datetime.now(UTC)
        with self.database.session() as session, session.begin():
            result = session.execute(
                update(AgentRunRecord)
                .where(
                    AgentRunRecord.id == agent_run_id,
                    or_(
                        AgentRunRecord.lease_owner.is_(None),
                        AgentRunRecord.lease_expires_at.is_(None),
                        AgentRunRecord.lease_expires_at < now,
                    ),
                )
                .values(
                    lease_owner=owner,
                    lease_expires_at=now + timedelta(seconds=lease_seconds),
                    heartbeat_at=now,
                    fencing_token=AgentRunRecord.fencing_token + 1,
                )
            )
            if result.rowcount != 1:
                return None
            record = session.get(AgentRunRecord, agent_run_id)
            if record is None:
                return None
            return AgentRun.model_validate_json(record.payload), record.fencing_token

    def heartbeat(
        self, agent_run_id: str, owner: str, fencing_token: int, lease_seconds: float
    ) -> bool:
        now = datetime.now(UTC)
        with self.database.session() as session, session.begin():
            result = session.execute(
                update(AgentRunRecord)
                .where(
                    AgentRunRecord.id == agent_run_id,
                    AgentRunRecord.lease_owner == owner,
                    AgentRunRecord.fencing_token == fencing_token,
                )
                .values(
                    heartbeat_at=now,
                    lease_expires_at=now + timedelta(seconds=lease_seconds),
                )
            )
            return result.rowcount == 1

    def owns_lease(self, agent_run_id: str, owner: str, fencing_token: int) -> bool:
        now = datetime.now(UTC)
        with self.database.session() as session:
            return session.scalar(select(func.count()).select_from(AgentRunRecord).where(
                AgentRunRecord.id == agent_run_id,
                AgentRunRecord.lease_owner == owner,
                AgentRunRecord.fencing_token == fencing_token,
                AgentRunRecord.lease_expires_at > now,
            )) == 1

    def release_claim(self, agent_run_id: str, owner: str, fencing_token: int) -> bool:
        with self.database.session() as session, session.begin():
            result = session.execute(
                update(AgentRunRecord)
                .where(
                    AgentRunRecord.id == agent_run_id,
                    AgentRunRecord.lease_owner == owner,
                    AgentRunRecord.fencing_token == fencing_token,
                )
                .values(lease_owner=None, lease_expires_at=None, heartbeat_at=None)
            )
            return result.rowcount == 1

    def list_events(self, agent_run_id: str, after_id: int = 0) -> list[AgentEvent]:
        with self.database.session() as session:
            exists = session.get(AgentRunRecord, agent_run_id)
            if exists is None:
                raise FileNotFoundError(agent_run_id)
            records = session.scalars(
                select(AgentEventRecord)
                .where(
                    AgentEventRecord.agent_run_id == agent_run_id,
                    AgentEventRecord.sequence > after_id,
                )
                .order_by(AgentEventRecord.sequence)
            ).all()
            return [AgentEvent.model_validate_json(record.payload) for record in records]

    def wait_for_events(
        self, agent_run_id: str, after_id: int, timeout_seconds: float
    ) -> list[AgentEvent]:
        with self._condition:
            events = self.list_events(agent_run_id, after_id)
            if events:
                return events
            self._condition.wait(timeout_seconds)
            return self.list_events(agent_run_id, after_id)

    def list_incomplete(self) -> list[AgentRun]:
        terminal = [status.value for status in (
            AgentRunStatus.COMPLETED,
            AgentRunStatus.FAILED,
            AgentRunStatus.CANCELLED,
            AgentRunStatus.BUDGET_EXHAUSTED,
        )]
        with self.database.session() as session:
            records = session.scalars(
                select(AgentRunRecord).where(AgentRunRecord.status.not_in(terminal))
            ).all()
            return [AgentRun.model_validate_json(record.payload) for record in records]

    def mark_step_running(
        self, agent_run_id: str, step_index: int, step_type: str, input_value: dict
    ) -> AgentStep:
        encoded = json.dumps(input_value, ensure_ascii=False, sort_keys=True, default=str)
        existing = self.get_step(agent_run_id, step_index)
        step = AgentStep(
            agent_run_id=agent_run_id,
            step_index=step_index,
            step_type=step_type,
            input_hash=__import__("hashlib").sha256(encoded.encode()).hexdigest(),
            status=AgentStepStatus.RUNNING,
            attempt=(existing.attempt + 1) if existing else 1,
            input=input_value,
            started_at=datetime.now(UTC).isoformat(),
        )
        return self.save_step(step)

    def save_span(self, span: TraceSpan) -> None:
        with self.database.session() as session, session.begin():
            record = session.get(TraceSpanRecord, span.id)
            values = {
                "trace_id": span.trace_id,
                "parent_span_id": span.parent_span_id,
                "organization_id": span.organization_id,
                "project_id": span.project_id,
                "agent_run_id": span.agent_run_id,
                "name": span.name,
                "status": span.status.value,
                "payload": span.model_dump_json(),
            }
            if record is None:
                session.add(TraceSpanRecord(id=span.id, **values))
            else:
                for key, value in values.items():
                    setattr(record, key, value)

    def list_spans(self, trace_id: str) -> list[TraceSpan]:
        with self.database.session() as session:
            records = session.scalars(
                select(TraceSpanRecord)
                .where(TraceSpanRecord.trace_id == trace_id)
                .order_by(TraceSpanRecord.started_at)
            ).all()
            return [TraceSpan.model_validate_json(record.payload) for record in records]

    def save_evaluation(
        self, dataset_hash: str, cases: list[GoldenCase], report: EvaluationReport
    ) -> str:
        dataset_id = f"golden-v2-{dataset_hash[:12]}"
        evaluation_run_id = f"eval_{uuid.uuid4().hex[:16]}"
        with self.database.session() as session, session.begin():
            dataset = session.get(EvaluationDatasetRecord, dataset_id)
            if dataset is None:
                session.add(EvaluationDatasetRecord(
                    id=dataset_id,
                    version=report.dataset_version,
                    name="ExperimentLens Golden Dataset v2",
                    content_hash=dataset_hash,
                    case_count=len(cases),
                ))
                session.flush()
            session.add(EvaluationRunRecord(
                id=evaluation_run_id,
                dataset_id=dataset_id,
                status="passed" if report.gate_passed else "failed",
                payload=report.model_dump_json(),
            ))
            session.flush()
            for result in report.results:
                session.add(EvaluationResultRecord(
                    evaluation_run_id=evaluation_run_id,
                    case_id=result.case_id,
                    passed=result.passed,
                    payload=result.model_dump_json(),
                ))
        return evaluation_run_id

    def latest_evaluation(self) -> tuple[str, EvaluationReport] | None:
        with self.database.session() as session:
            record = session.scalar(
                select(EvaluationRunRecord).order_by(EvaluationRunRecord.created_at.desc()).limit(1)
            )
            if record is None:
                return None
            return record.id, EvaluationReport.model_validate_json(record.payload)


def _parse_time(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None
