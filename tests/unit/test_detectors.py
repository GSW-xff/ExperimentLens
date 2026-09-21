import pandas as pd
import pytest
from experimentlens.detectors import DETECTOR_REGISTRY, run_detectors
from experimentlens.domain import SchemaMapping


def mapping():
    return SchemaMapping(
        run_id="run_id",
        group="group",
        seed="seed",
        status="status",
        primary_metric="score",
        baseline_group="base",
        metric_columns=["score"],
    )


def context_frames(values=(0.8, 0.81, 0.79, 0.8), candidate=(0.9, 0.91, 0.89, 0.9)):
    rows = []
    for group, group_values in (("base", values), ("candidate", candidate)):
        for index, value in enumerate(group_values):
            rows.append({
                "run_id": f"{group}-{index}", "group": group, "seed": index,
                "status": "completed", "value": value,
            })
    return pd.DataFrame(rows)


def groups(data):
    return [
        {
            "group": group,
            "n": len(frame),
            "std": float(frame["value"].std()),
            "run_ids": frame["run_id"].tolist(),
        }
        for group, frame in data.groupby("group")
    ]


def test_registry_exposes_each_deterministic_detector():
    assert {"run_integrity", "metric_outlier", "seed_instability", "dataset_drift", "log_errors"} <= set(DETECTOR_REGISTRY)


@pytest.mark.parametrize(
    ("mutate", "expected_type"),
    [
        (lambda data: data.assign(status=data["status"].mask(data.index == 0, "failed")), "failed_run"),
        (lambda data: pd.concat([data, data.iloc[[0]]], ignore_index=True), "duplicate_run"),
        (lambda data: data.assign(seed=data["seed"].mask(data.index == 0)), "missing_seed"),
    ],
)
def test_run_integrity_detector_positive_cases(mutate, expected_type):
    data = mutate(context_frames())
    findings = run_detectors(data, pd.DataFrame(), [], mapping(), groups(data))
    assert expected_type in {finding.type for finding in findings}


def test_detectors_have_clean_negative_case():
    data = context_frames()
    findings = run_detectors(data, pd.DataFrame(), [], mapping(), groups(data))
    assert findings == []


def test_outlier_detector_handles_boundary_and_positive_case():
    boundary = context_frames(candidate=(0.90, 0.90, 0.90, 0.90))
    assert "metric_outlier" not in {
        item.type for item in run_detectors(boundary, pd.DataFrame(), [], mapping(), groups(boundary))
    }
    positive = context_frames(candidate=(0.90, 0.901, 0.899, 1.2))
    assert "metric_outlier" in {
        item.type for item in run_detectors(positive, pd.DataFrame(), [], mapping(), groups(positive))
    }


def test_log_and_dataset_detectors_create_source_backed_evidence():
    data = context_frames()
    params = pd.DataFrame([
        {"run_id": "base-0", "key": "dataset_version", "value": "v1"},
        {"run_id": "candidate-0", "key": "dataset_version", "value": "v2"},
    ])
    logs = [{"source": "candidate.log", "line": 8, "text": "CUDA out of memory"}]
    findings = run_detectors(data, params, logs, mapping(), groups(data))
    by_type = {finding.type: finding for finding in findings}
    assert by_type["dataset_drift"].evidence_refs[0].kind == "param"
    assert by_type["log_out_of_memory"].evidence_refs[0].id == "candidate.log:8"
