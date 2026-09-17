from pathlib import Path

import pandas as pd
from experimentlens.analysis import analyze
from experimentlens.ingestion import infer_mapping, normalize, parse_file

SAMPLE_DIR = Path(__file__).parents[1] / "examples" / "test-data"


def analyze_sample(filename: str):
    path = SAMPLE_DIR / filename
    bundle = parse_file(path)
    frame = bundle.tables[0]
    mapping, _ = infer_mapping(frame)
    runs, metrics, params = normalize(frame, mapping)
    return frame, mapping, analyze(runs, metrics, params, bundle.logs, mapping)


def test_polyp_segmentation_sample_exercises_failure_and_seed_instability():
    frame, mapping, result = analyze_sample("polyp_segmentation_results.csv")

    assert frame["run_id"].is_unique
    assert mapping.primary_metric == "dice_f1"
    assert mapping.baseline_group == "UNet Baseline"
    assert mapping.metric_direction == "maximize"
    assert result["summary"]["run_count"] == 15
    assert result["summary"]["failed_runs"] == 1
    finding_types = {item["type"] for item in result["findings"]}
    assert {"failed_run", "invalid_metric", "seed_instability"} <= finding_types


def test_sentiment_sample_exercises_outlier_and_unstable_mean_gain():
    frame, mapping, result = analyze_sample("sentiment_classification_results.csv")

    assert frame["run_id"].is_unique
    assert mapping.primary_metric == "accuracy"
    assert mapping.baseline_group == "RoBERTa Baseline"
    comparison = next(
        item for item in result["summary"]["comparison"] if item["group"] == "LoRA Rank 8"
    )
    assert comparison["mean_delta"] > 0
    finding_types = {item["type"] for item in result["findings"]}
    assert {"metric_outlier", "seed_instability"} <= finding_types


def test_forecasting_sample_exercises_minimization_and_dataset_drift():
    frame, mapping, result = analyze_sample("electricity_forecasting_results.csv")

    assert frame["run_id"].is_unique
    assert mapping.primary_metric == "loss"
    assert mapping.baseline_group == "LSTM Baseline"
    assert mapping.metric_direction == "minimize"
    comparisons = {item["group"]: item for item in result["summary"]["comparison"]}
    assert comparisons["PatchTST"]["mean_delta"] < 0
    assert "dataset_drift" in {item["type"] for item in result["findings"]}


def test_all_samples_follow_the_result_table_contract():
    required = {"run_id", "group", "seed", "status", "duration_seconds"}
    paths = sorted(SAMPLE_DIR.glob("*_results.csv"))

    assert len(paths) == 3
    for path in paths:
        frame = pd.read_csv(path)
        assert required <= set(frame.columns)
        assert frame["run_id"].is_unique
        assert frame["group"].nunique() >= 2
        assert frame["seed"].notna().all()
