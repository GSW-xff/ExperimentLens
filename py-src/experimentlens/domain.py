from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


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
    AWAITING_APPROVAL = "awaiting_approval"


class ToolCallStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"


class SpanStatus(StrEnum):
    OK = "ok"
    ERROR = "error"


class MetricRole(StrEnum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    CONSTRAINT = "constraint"
    RESOURCE = "resource"


class MetricDirection(StrEnum):
    MAXIMIZE = "maximize"
    MINIMIZE = "minimize"


class MetricDefinition(BaseModel):
    key: str
    display_name: str | None = None
    role: MetricRole = MetricRole.SECONDARY
    direction: MetricDirection = MetricDirection.MAXIMIZE
    unit: str | None = None
    aggregation: str = "mean"
    valid_min: float | None = None
    valid_max: float | None = None
    constraint_operator: str | None = None
    constraint_value: float | None = None

    @model_validator(mode="after")
    def validate_constraint(self):
        if self.role == MetricRole.CONSTRAINT:
            if self.constraint_operator not in {"lt", "lte", "gt", "gte"}:
                raise ValueError("constraint metric requires lt, lte, gt or gte operator")
            if self.constraint_value is None:
                raise ValueError("constraint metric requires constraint_value")
        return self


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
    step_count: int = Field(default=0, ge=0)
    model: str = "deterministic-fallback"
    tool_calls: list[ToolCall] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    answer: str | None = None
    error: str | None = None
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)
    started_at: str | None = None
    completed_at: str | None = None


class AgentEvent(BaseModel):
    id: int = Field(ge=1)
    agent_run_id: str
    type: str
    created_at: str = Field(default_factory=utc_now)
    payload: dict[str, Any] = Field(default_factory=dict)


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
    metric_definitions: list[MetricDefinition] = Field(default_factory=list)
    parameter_columns: list[str] = Field(default_factory=list)

    @field_validator("metric_direction")
    @classmethod
    def validate_direction(cls, value: str) -> str:
        if value not in {"maximize", "minimize"}:
            raise ValueError("metric_direction must be maximize or minimize")
        return value

    @model_validator(mode="after")
    def populate_metric_definitions(self):
        keys = list(dict.fromkeys([self.primary_metric, *self.metric_columns]))
        existing = {definition.key: definition for definition in self.metric_definitions}
        definitions = []
        for key in keys:
            definition = existing.get(key)
            if definition is None:
                definition = MetricDefinition(
                    key=key,
                    display_name=key,
                    role=MetricRole.PRIMARY if key == self.primary_metric else MetricRole.SECONDARY,
                    direction=(
                        MetricDirection(self.metric_direction)
                        if key == self.primary_metric
                        else MetricDirection.MAXIMIZE
                    ),
                )
            elif key == self.primary_metric and definition.role != MetricRole.PRIMARY:
                definition = definition.model_copy(update={"role": MetricRole.PRIMARY})
            definitions.append(definition)
        self.metric_definitions = definitions
        self.metric_columns = keys
        return self


class Project(BaseModel):
    schema_version: int = Field(default=2, ge=2)
    id: str
    name: str
    objective: str
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)
    state: str = "empty"
    experiment_type: str = "general"
    domain_tags: list[str] = Field(default_factory=list)
    owner_id: str | None = None
    sources: list[dict[str, Any]] = Field(default_factory=list)
    mapping: SchemaMapping | None = None
    metric_definitions: list[MetricDefinition] = Field(default_factory=list)
