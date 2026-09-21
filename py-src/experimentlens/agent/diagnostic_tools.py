from __future__ import annotations

from typing import Any

import pandas as pd
from pydantic import BaseModel, Field

from ..domain import EvidenceRef
from ..repositories.interfaces import ExperimentRepository
from .tool_registry import RegisteredTool, ToolRegistry


class ListRunsInput(BaseModel):
    group: str | None = None
    status: str | None = None
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class ListRunsOutput(BaseModel):
    runs: list[dict[str, Any]]
    total: int
    evidence_refs: list[EvidenceRef]


class CompareGroupsInput(BaseModel):
    metric: str | None = None
    baseline: str | None = None
    groups: list[str] = Field(default_factory=list, max_length=20)


class CompareGroupsOutput(BaseModel):
    metric: str
    baseline: str
    groups: list[dict[str, Any]]
    evidence_refs: list[EvidenceRef]


class SearchLogsInput(BaseModel):
    query: str = Field(min_length=1, max_length=200)
    run_ids: list[str] = Field(default_factory=list, max_length=50)
    limit: int = Field(default=20, ge=1, le=100)


class SearchLogsOutput(BaseModel):
    matches: list[dict[str, Any]]
    evidence_refs: list[EvidenceRef]


class DiffConfigsInput(BaseModel):
    run_ids: list[str] = Field(default_factory=list, max_length=20)
    groups: list[str] = Field(default_factory=list, max_length=10)


class DiffConfigsOutput(BaseModel):
    run_ids: list[str]
    differences: dict[str, dict[str, str]]
    evidence_refs: list[EvidenceRef]


def build_diagnostic_registry(
    repository: ExperimentRepository, project_id: str
) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(RegisteredTool(
        name="list_runs",
        description="List runs in the current project using optional group and status filters.",
        input_model=ListRunsInput,
        output_model=ListRunsOutput,
        handler=lambda arguments: _list_runs(repository, project_id, arguments),
    ))
    registry.register(RegisteredTool(
        name="compare_groups",
        description="Compare group means for one metric inside the current project.",
        input_model=CompareGroupsInput,
        output_model=CompareGroupsOutput,
        handler=lambda arguments: _compare_groups(repository, project_id, arguments),
    ))
    registry.register(RegisteredTool(
        name="search_logs",
        description="Search imported logs in the current project and return source-backed evidence.",
        input_model=SearchLogsInput,
        output_model=SearchLogsOutput,
        handler=lambda arguments: _search_logs(repository, project_id, arguments),
    ))
    registry.register(RegisteredTool(
        name="diff_configs",
        description="Compare configuration values for selected runs or groups in the current project.",
        input_model=DiffConfigsInput,
        output_model=DiffConfigsOutput,
        handler=lambda arguments: _diff_configs(repository, project_id, arguments),
    ))
    return registry


def _list_runs(
    repository: ExperimentRepository, project_id: str, arguments: ListRunsInput
) -> dict[str, Any]:
    runs = repository.read_frame(project_id, "runs")
    if arguments.group:
        runs = runs[runs["group"].astype(str) == arguments.group]
    if arguments.status:
        runs = runs[runs["status"].astype(str).str.lower() == arguments.status.lower()]
    total = len(runs)
    selected = runs.iloc[arguments.offset : arguments.offset + arguments.limit]
    records = _records(selected)
    return {
        "runs": records,
        "total": total,
        "evidence_refs": [
            EvidenceRef(id=str(row["run_id"]), kind="run", label=str(row["run_id"]))
            for row in records
        ],
    }


def _compare_groups(
    repository: ExperimentRepository, project_id: str, arguments: CompareGroupsInput
) -> dict[str, Any]:
    project = repository.get_project(project_id)
    if not project.mapping:
        raise ValueError("project has no confirmed mapping")
    metric = arguments.metric or project.mapping.primary_metric
    if metric not in project.mapping.metric_columns:
        raise ValueError(f"unknown metric: {metric}")
    baseline = arguments.baseline or project.mapping.baseline_group
    runs = repository.read_frame(project_id, "runs")
    metrics = repository.read_frame(project_id, "metrics")
    values = metrics.loc[metrics["key"] == metric, ["run_id", "value"]]
    data = runs[["run_id", "group"]].merge(values, on="run_id", how="left")
    if arguments.groups:
        allowed = set([baseline, *arguments.groups])
        data = data[data["group"].astype(str).isin(allowed)]
    groups = []
    refs = []
    for group, frame in data.groupby("group", sort=True):
        valid = pd.to_numeric(frame["value"], errors="coerce").dropna()
        run_ids = frame.loc[frame["value"].notna(), "run_id"].astype(str).tolist()
        groups.append({
            "group": str(group),
            "n": int(len(valid)),
            "mean": float(valid.mean()) if not valid.empty else None,
            "std": float(valid.std(ddof=1)) if len(valid) > 1 else 0.0,
            "run_ids": run_ids,
        })
        refs.extend(
            EvidenceRef(id=f"{run_id}:{metric}", kind="metric", label=f"{run_id} · {metric}")
            for run_id in run_ids
        )
    return {"metric": metric, "baseline": baseline, "groups": groups, "evidence_refs": refs}


def _search_logs(
    repository: ExperimentRepository, project_id: str, arguments: SearchLogsInput
) -> dict[str, Any]:
    logs = repository.read_json(project_id, "normalized/artifacts.json", [])
    query = arguments.query.casefold()
    allowed_runs = set(arguments.run_ids)
    matches = []
    refs = []
    for record in logs:
        if query not in str(record.get("text", "")).casefold():
            continue
        if allowed_runs and record.get("run_id") not in allowed_runs:
            continue
        item = {
            "source": record.get("source", "log"),
            "line": record.get("line", "?"),
            "run_id": record.get("run_id"),
            "text": str(record.get("text", ""))[:500],
        }
        matches.append(item)
        refs.append(EvidenceRef(
            id=f"{item['source']}:{item['line']}",
            kind="log",
            label=f"{item['source']} 第 {item['line']} 行",
            detail=item["text"],
        ))
        if len(matches) >= arguments.limit:
            break
    return {"matches": matches, "evidence_refs": refs}


def _diff_configs(
    repository: ExperimentRepository, project_id: str, arguments: DiffConfigsInput
) -> dict[str, Any]:
    runs = repository.read_frame(project_id, "runs")
    selected_ids = set(arguments.run_ids)
    if arguments.groups:
        selected_ids.update(
            runs.loc[runs["group"].astype(str).isin(arguments.groups), "run_id"].astype(str)
        )
    if not selected_ids:
        selected_ids.update(runs["run_id"].astype(str).head(20))
    params = repository.read_frame(project_id, "params")
    params = params[params["run_id"].astype(str).isin(selected_ids)]
    differences: dict[str, dict[str, str]] = {}
    refs = []
    for key, frame in params.groupby("key", sort=True):
        values = {str(row.run_id): str(row.value) for row in frame.itertuples()}
        if len(set(values.values())) > 1:
            differences[str(key)] = values
            refs.extend(
                EvidenceRef(
                    id=f"{run_id}:{key}", kind="param", label=f"{run_id} · {key}={value}"
                )
                for run_id, value in values.items()
            )
    return {
        "run_ids": sorted(selected_ids),
        "differences": differences,
        "evidence_refs": refs[:100],
    }


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return [
        {key: None if pd.isna(value) else value for key, value in record.items()}
        for record in frame.to_dict(orient="records")
    ]
