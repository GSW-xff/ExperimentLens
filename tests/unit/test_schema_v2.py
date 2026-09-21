import json

import pandas as pd
from experimentlens.analysis import analyze
from experimentlens.domain import MetricDefinition, MetricRole, Project, SchemaMapping
from experimentlens.migrations import migrate_project_payload
from experimentlens.workspace import Workspace


def test_v1_payload_migrates_to_v2_idempotently():
    original = {
        "id": "p1",
        "name": "Legacy",
        "objective": "compare",
        "mapping": {
            "run_id": "run_id",
            "group": "group",
            "primary_metric": "accuracy",
            "metric_direction": "maximize",
            "baseline_group": "base",
            "metric_columns": ["accuracy", "latency_p95"],
            "parameter_columns": [],
        },
    }
    migrated, manifest = migrate_project_payload(original)
    repeated, repeated_manifest = migrate_project_payload(migrated)

    assert migrated["schema_version"] == 2
    assert migrated["metric_definitions"][0]["role"] == "primary"
    assert manifest["from_version"] == 1
    assert repeated == migrated
    assert repeated_manifest is None
    assert "schema_version" not in original


def test_workspace_persists_backup_and_manifest_during_v1_migration(tmp_path):
    workspace = Workspace(tmp_path / "workspace")
    directory = workspace.project_dir("legacy")
    directory.mkdir(parents=True)
    payload = {"id": "legacy", "name": "Legacy", "objective": "test"}
    (directory / "project.json").write_text(json.dumps(payload), encoding="utf-8")

    project = workspace.get_project("legacy")

    assert project.schema_version == 2
    assert (directory / "migration-backups" / "v1-project.json").exists()
    assert (directory / "migration-backups" / "v1-to-v2-manifest.json").exists()
    assert json.loads((directory / "project.json").read_text())["schema_version"] == 2


def test_multi_metric_analysis_reports_constraints_and_pareto_frontier():
    mapping = SchemaMapping(
        run_id="run_id",
        group="group",
        primary_metric="accuracy",
        metric_direction="maximize",
        baseline_group="base",
        metric_columns=["accuracy", "latency_p95"],
        parameter_columns=[],
        metric_definitions=[
            MetricDefinition(key="accuracy", role="primary", direction="maximize"),
            MetricDefinition(
                key="latency_p95",
                role=MetricRole.CONSTRAINT,
                direction="minimize",
                unit="ms",
                constraint_operator="lte",
                constraint_value=50,
            ),
        ],
    )
    runs = pd.DataFrame([
        {"run_id": "b1", "group": "base", "status": "completed", "seed": 1},
        {"run_id": "b2", "group": "base", "status": "completed", "seed": 2},
        {"run_id": "c1", "group": "candidate", "status": "completed", "seed": 1},
        {"run_id": "c2", "group": "candidate", "status": "completed", "seed": 2},
    ])
    metrics = pd.DataFrame([
        {"run_id": "b1", "key": "accuracy", "value": 0.80},
        {"run_id": "b2", "key": "accuracy", "value": 0.81},
        {"run_id": "c1", "key": "accuracy", "value": 0.86},
        {"run_id": "c2", "key": "accuracy", "value": 0.87},
        {"run_id": "b1", "key": "latency_p95", "value": 45},
        {"run_id": "b2", "key": "latency_p95", "value": 47},
        {"run_id": "c1", "key": "latency_p95", "value": 49},
        {"run_id": "c2", "key": "latency_p95", "value": 54},
    ])
    params = pd.DataFrame(columns=["run_id", "key", "value", "value_type"])

    result = analyze(runs, metrics, params, [], mapping)

    constraint = result["summary"]["constraints"][0]
    assert constraint["violation_count"] == 1
    assert constraint["violating_run_ids"] == ["c2"]
    assert result["summary"]["constraints_satisfied"] is False
    assert {item["key"] for item in result["summary"]["metric_summaries"]} == {
        "accuracy",
        "latency_p95",
    }


def test_new_projects_use_schema_v2():
    project = Project(id="p1", name="new", objective="test")
    assert project.schema_version == 2
    assert project.experiment_type == "general"
