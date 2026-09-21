import pandas as pd
import pytest
from experimentlens.agent.diagnostic_tools import build_diagnostic_registry
from experimentlens.domain import SchemaMapping
from experimentlens.workspace import Workspace


@pytest.fixture
def tool_project(tmp_path):
    workspace = Workspace(tmp_path / "workspace")
    project = workspace.create_project("tools", "diagnose")
    project.mapping = SchemaMapping(
        run_id="run_id",
        group="group",
        primary_metric="accuracy",
        baseline_group="base",
        metric_columns=["accuracy"],
        parameter_columns=["batch_size"],
    )
    workspace.save_project(project)
    workspace.write_frame(project.id, "runs", pd.DataFrame([
        {"run_id": "b1", "group": "base", "status": "completed"},
        {"run_id": "c1", "group": "candidate", "status": "completed"},
    ]))
    workspace.write_frame(project.id, "metrics", pd.DataFrame([
        {"run_id": "b1", "key": "accuracy", "value": 0.8},
        {"run_id": "c1", "key": "accuracy", "value": 0.9},
    ]))
    workspace.write_frame(project.id, "params", pd.DataFrame([
        {"run_id": "b1", "key": "batch_size", "value": "16"},
        {"run_id": "c1", "key": "batch_size", "value": "32"},
    ]))
    workspace.write_json(project.id, "normalized/artifacts.json", [
        {"source": "c1.log", "line": 7, "run_id": "c1", "text": "CUDA out of memory"}
    ])
    return workspace, project


def test_read_only_tools_return_project_scoped_evidence(tool_project):
    workspace, project = tool_project
    registry = build_diagnostic_registry(workspace, project.id)

    listed = registry.invoke("list_runs", {"group": "candidate"})
    compared = registry.invoke("compare_groups", {})
    logs = registry.invoke("search_logs", {"query": "out of memory"})
    configs = registry.invoke("diff_configs", {"run_ids": ["b1", "c1"]})

    assert [row["run_id"] for row in listed.runs] == ["c1"]
    assert {row["group"] for row in compared.groups} == {"base", "candidate"}
    assert logs.evidence_refs[0].id == "c1.log:7"
    assert configs.differences["batch_size"] == {"b1": "16", "c1": "32"}
    assert all(tool["type"] == "function" for tool in registry.model_tools())


def test_tools_reject_unknown_metric_and_extra_scope_argument(tool_project):
    workspace, project = tool_project
    registry = build_diagnostic_registry(workspace, project.id)
    with pytest.raises(ValueError, match="unknown metric"):
        registry.invoke("compare_groups", {"metric": "secret"})
    with pytest.raises(ValueError, match="unexpected arguments"):
        registry.invoke("list_runs", {"project_id": "other"})
