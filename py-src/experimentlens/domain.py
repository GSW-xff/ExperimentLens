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
