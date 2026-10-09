from pathlib import Path

from experimentlens.evaluation import Trajectory, evaluate_cases, load_dataset
from experimentlens.evaluation.executor import EvaluationExecutor
from experimentlens.persistence import Database
from experimentlens.repositories.local import LocalRepository


def _dataset_path() -> Path:
    return Path(__file__).parents[2] / "evals/cases/golden-v2.jsonl"


def test_golden_dataset_has_versioned_safety_and_reliability_coverage():
    dataset_hash, cases = load_dataset(_dataset_path())

    assert len(cases) == 30
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


def test_evaluation_executor_collects_real_agent_trajectories_deterministically(tmp_path):
    dataset_hash, cases = load_dataset(_dataset_path())
    selected = cases[:3]

    def run_once(name: str):
        database = Database(f"sqlite:///{tmp_path / name / 'evaluation.db'}")
        database.create_schema()
        executor = EvaluationExecutor(
            LocalRepository(tmp_path / name / "workspace"),
            database,
            cases=selected,
            dataset_hash=dataset_hash,
        )
        return executor.execute()

    first = run_once("first")
    second = run_once("second")

    assert first.gate_passed is True
    assert first.pass_rate == second.pass_rate == 1
    assert first.invalid_evidence_rate == second.invalid_evidence_rate == 0
    assert first.average_tokens == second.average_tokens
    assert first.versions["dataset_hash"] == dataset_hash
    assert first.versions["tool_schema_hash"] == second.versions["tool_schema_hash"]
