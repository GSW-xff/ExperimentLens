from pathlib import Path

from experimentlens.evaluation import Trajectory, evaluate_cases, load_dataset


def _dataset_path() -> Path:
    return Path(__file__).parents[2] / "evals/cases/golden-v2.jsonl"


def test_golden_dataset_has_versioned_safety_and_reliability_coverage():
    dataset_hash, cases = load_dataset(_dataset_path())

    assert len(cases) >= 20
    assert len(dataset_hash) == 64
    tags = {tag for case in cases for tag in case.tags}
    assert {"security", "reliability", "prompt-injection", "tenant-isolation"} <= tags


def test_evaluation_quality_gate_enforces_zero_tolerance_metrics():
    dataset_hash, cases = load_dataset(_dataset_path())
    trajectories = [Trajectory(
        case_id=case.id,
        tools=case.required_tools,
        evidence_ids=[f"evidence-{index}" for index in range(case.minimum_evidence)],
        latency_ms=10,
        token_count=20,
    ) for case in cases]

    passing = evaluate_cases(cases, trajectories, dataset_hash=dataset_hash)
    assert passing.gate_passed is True
    assert passing.pass_rate == 1

    trajectories[0].invalid_evidence_ids = ["fabricated"]
    failing = evaluate_cases(cases, trajectories, dataset_hash=dataset_hash)
    assert failing.gate_passed is False
    assert failing.invalid_evidence_rate > 0
    assert failing.results[0].failures == ["invalid evidence"]
