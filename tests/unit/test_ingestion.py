from pathlib import Path

import pandas as pd
from experimentlens.ingestion import infer_mapping, normalize, parse_file


def test_parse_supported_result_and_config_files(tmp_path: Path):
    csv_path = tmp_path / "results.csv"
    csv_path.write_text("run_id,group,seed,accuracy\nr1,base,1,0.8\nr2,new,2,0.9\n", encoding="utf-8")
    yaml_path = tmp_path / "r1.yaml"
    yaml_path.write_text("run_id: r1\nbatch_size: 32\n", encoding="utf-8")
    log_path = tmp_path / "r1.log"
    log_path.write_text("epoch 1 ok\nRuntimeError: CUDA out of memory\n", encoding="utf-8")

    assert len(parse_file(csv_path).tables[0]) == 2
    assert parse_file(yaml_path).configs[0]["batch_size"] == 32
    assert parse_file(log_path).logs[1]["line"] == 2


def test_infer_and_normalize_experiment_schema():
    frame = pd.DataFrame(
        [
            {"run_id": "r1", "group": "baseline", "seed": 1, "accuracy": 0.8, "batch_size": 16},
            {"run_id": "r2", "group": "candidate", "seed": 2, "accuracy": 0.9, "batch_size": 32},
        ]
    )
    mapping, confidence = infer_mapping(frame)
    runs, metrics, params = normalize(frame, mapping)

    assert mapping.primary_metric == "accuracy"
    assert mapping.baseline_group == "baseline"
    assert confidence["primary_metric"] >= 0.9
    assert runs.to_dict(orient="records")[1]["group"] == "candidate"
    assert metrics[metrics["run_id"] == "r2"].iloc[0]["value"] == 0.9
    assert "batch_size" in set(params["key"])


def test_rejects_unknown_file_type(tmp_path: Path):
    path = tmp_path / "payload.exe"
    path.write_bytes(b"not executable")
    try:
        parse_file(path)
    except ValueError as error:
        assert "不支持" in str(error)
    else:
        raise AssertionError("unknown type should be rejected")


def test_infers_general_quality_resource_and_cost_metric_aliases():
    cases = {
        "iou": "maximize",
        "mae": "minimize",
        "rmse": "minimize",
        "reward": "maximize",
        "latency_p95": "minimize",
        "throughput": "maximize",
        "memory_gb": "minimize",
        "cost_usd": "minimize",
    }
    for metric, direction in cases.items():
        frame = pd.DataFrame({
            "run_id": ["r1", "r2"],
            "group": ["baseline", "candidate"],
            metric: [1.0, 2.0],
        })
        mapping, _ = infer_mapping(frame)
        assert mapping.primary_metric == metric
        assert mapping.metric_direction == direction
