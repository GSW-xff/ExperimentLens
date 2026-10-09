from experimentlens.reliability import run_reliability_experiment


def test_reliability_experiment_recovers_worker_and_preserves_events(tmp_path):
    report = run_reliability_experiment(
        run_count=6,
        worker_count=2,
        workspace_root=tmp_path / "workspace",
        database_url=f"sqlite:///{tmp_path / 'reliability.db'}",
    )

    results = report["results"]
    assert results["completion_rate"] == 1
    assert results["worker_crashes_injected"] == 1
    assert results["duplicate_tool_calls"] == 0
    assert results["lost_events"] == 0
    assert results["sse_replay_failures"] == 0
    assert results["crash_recovery_ms"] > 0
