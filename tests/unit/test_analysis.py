import pandas as pd
from experimentlens.analysis import analyze, answer_question
from experimentlens.domain import SchemaMapping


def mapping():
    return SchemaMapping(
        run_id="run_id",
        group="group",
        seed="seed",
        status="status",
        duration="duration_seconds",
        primary_metric="accuracy",
        metric_direction="maximize",
        baseline_group="baseline",
        metric_columns=["accuracy"],
    )


def frames(candidate_values=(0.85, 0.86, 0.87), failed=False):
    base_values = (0.80, 0.81, 0.79)
    rows = []
    metric_rows = []
    for group, values in (("baseline", base_values), ("candidate", candidate_values)):
        for index, value in enumerate(values):
            run_id = f"{group}-{index}"
            status = "failed" if failed and group == "candidate" and index == 1 else "completed"
            rows.append({"run_id": run_id, "group": group, "seed": index, "status": status, "duration_seconds": 100})
            metric_rows.append({"run_id": run_id, "key": "accuracy", "value": None if status == "failed" else value})
    return pd.DataFrame(rows), pd.DataFrame(metric_rows), pd.DataFrame(columns=["run_id", "key", "value", "value_type"])


def test_stable_candidate_has_positive_comparison():
    runs, metrics, params = frames()
    result = analyze(runs, metrics, params, [], mapping())
    comparison = result["summary"]["comparison"][0]

    assert comparison["mean_delta"] > 0.04
    assert comparison["confidence_interval"][0] > 0
    assert "方向一致" in result["summary"]["conclusion"]


def test_failed_run_and_oom_log_create_traceable_findings_and_hypothesis():
    runs, metrics, params = frames(failed=True)
    logs = [{"source": "candidate-1.log", "line": 99, "text": "RuntimeError: CUDA out of memory"}]
    result = analyze(runs, metrics, params, logs, mapping())

    types = {finding["type"] for finding in result["findings"]}
    assert {"failed_run", "invalid_metric", "log_out_of_memory"} <= types
    hypothesis = next(item for item in result["hypotheses"] if item["id"] == "hyp_memory_pressure")
    assert hypothesis["supporting_evidence"]
    assert hypothesis["verification_plan"]


def test_question_answer_uses_analysis_evidence():
    runs, metrics, params = frames(candidate_values=(0.70, 0.86, 0.99))
    result = analyze(runs, metrics, params, [], mapping())
    response = answer_question("哪些 seed 的波动最大？", result)

    assert "标准差" in response["answer"]
    assert response["basis"] == "deterministic_analysis"
    assert response["evidence_refs"]
