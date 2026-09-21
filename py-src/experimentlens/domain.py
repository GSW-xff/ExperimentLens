from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class Severity(StrEnum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class AgentRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BUDGET_EXHAUSTED = "budget_exhausted"


class ToolCallStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"


class SpanStatus(StrEnum):
    OK = "ok"
    ERROR = "error"


class EvidenceRef(BaseModel):
    id: str
    kind: str
    label: str
    detail: str | None = None


class Finding(BaseModel):
    id: str
    type: str
    severity: Severity
    title: str
    description: str
    evidence_refs: list[EvidenceRef]
    detector: str
    detector_version: str = "1.0"
    confidence: float = Field(ge=0, le=1)


class Hypothesis(BaseModel):
    id: str
    description: str
    supporting_evidence: list[EvidenceRef]
    contradicting_evidence: list[EvidenceRef] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    verification_plan: str
    status: str = "open"


class ExperimentProposal(BaseModel):
    id: str
    title: str
    hypothesis_id: str
    changed_variable: str
    fixed_conditions: list[str]
    seeds: list[int]
    expected_observation: str
    interpretation: str
    priority: str
    estimated_cost: str
    status: str = "proposed"


class ToolCall(BaseModel):
    id: str
    agent_run_id: str
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    status: ToolCallStatus = ToolCallStatus.PENDING
    read_only: bool = True
    requires_approval: bool = False
    output_summary: str | None = None
    error: str | None = None
    created_at: str = Field(default_factory=utc_now)


class AgentRun(BaseModel):
    id: str
    project_id: str
    question: str
    status: AgentRunStatus = AgentRunStatus.PENDING
    max_steps: int = Field(default=8, ge=1, le=50)
    token_budget: int = Field(default=8000, ge=1)
    used_tokens: int = Field(default=0, ge=0)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    answer: str | None = None
    error: str | None = None
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)


class TraceSpan(BaseModel):
    id: str
    trace_id: str
    parent_span_id: str | None = None
    name: str
    status: SpanStatus = SpanStatus.OK
    started_at: str = Field(default_factory=utc_now)
    ended_at: str | None = None
    duration_ms: float | None = Field(default=None, ge=0)
    input_digest: str | None = None
    output_digest: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    error_category: str | None = None


class EvaluationCase(BaseModel):
    id: str
    project_fixture: str
    question: str
    expected_findings: list[str] = Field(default_factory=list)
    allowed_hypotheses: list[str] = Field(default_factory=list)
    forbidden_behaviors: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class SchemaMapping(BaseModel):
    run_id: str
    group: str
    seed: str | None = None
    status: str | None = None
    duration: str | None = None
    primary_metric: str
    metric_direction: str = "maximize"
    baseline_group: str
    metric_columns: list[str] = Field(default_factory=list)
    parameter_columns: list[str] = Field(default_factory=list)

    @field_validator("metric_direction")
    @classmethod
    def validate_direction(cls, value: str) -> str:
        if value not in {"maximize", "minimize"}:
            raise ValueError("metric_direction must be maximize or minimize")
        return value


class Project(BaseModel):
    id: str
    name: str
    objective: str
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)
    state: str = "empty"
    sources: list[dict[str, Any]] = Field(default_factory=list)
    mapping: SchemaMapping | None = None
