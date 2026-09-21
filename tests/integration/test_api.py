import io

from experimentlens.app import create_app


def test_complete_upload_analysis_chat_and_report_flow(tmp_path):
    app = create_app({"TESTING": True, "WORKSPACE_ROOT": tmp_path / "workspace"})
    client = app.test_client()

    created = client.post("/api/projects", json={"name": "API test", "objective": "compare models"})
    assert created.status_code == 201
    project_id = created.get_json()["id"]

    results = b"run_id,group,seed,status,accuracy,duration_seconds,batch_size\nb1,baseline,1,completed,0.80,100,16\nb2,baseline,2,completed,0.81,100,16\nc1,candidate,1,completed,0.86,110,32\nc2,candidate,2,failed,,80,32\n"
    log = b"run=c2 RuntimeError: CUDA out of memory\n"
    uploaded = client.post(
        f"/api/projects/{project_id}/sources/upload",
        data={"files": [(io.BytesIO(results), "results.csv"), (io.BytesIO(log), "c2.log")]},
        content_type="multipart/form-data",
    )
    assert uploaded.status_code == 200
    mapping = uploaded.get_json()["mapping"]
    assert mapping["primary_metric"] == "accuracy"

    confirmed = client.post(f"/api/projects/{project_id}/schema/confirm", json=mapping)
    assert confirmed.status_code == 200
    assert confirmed.get_json()["run_count"] == 4

    analyzed = client.post(f"/api/projects/{project_id}/analysis/run")
    assert analyzed.status_code == 200
    payload = analyzed.get_json()
    assert payload["summary"]["run_count"] == 4
    assert any(item["evidence_refs"] for item in payload["findings"])

    runs = client.get(f"/api/projects/{project_id}/runs")
    assert runs.status_code == 200
    assert runs.get_json()[0]["params"]

    chat = client.post(f"/api/projects/{project_id}/chat", json={"question": "为什么有异常？"})
    assert chat.status_code == 200
    assert chat.get_json()["basis"] == "deterministic_analysis"

    report = client.post(f"/api/projects/{project_id}/reports/generate")
    assert report.status_code == 200
    assert "## 异常与证据" in report.get_json()["markdown"]

    saved = client.put(
        f"/api/projects/{project_id}/reports/analysis-report",
        json={"html": "<h1>Edited report</h1>"},
    )
    assert saved.status_code == 200
    downloaded = client.get(f"/api/projects/{project_id}/reports/download")
    assert downloaded.status_code == 200
    assert b"Edited report" in downloaded.data


def test_demo_project_is_ready_to_explore(tmp_path):
    app = create_app({"TESTING": True, "WORKSPACE_ROOT": tmp_path / "workspace"})
    client = app.test_client()
    response = client.post("/api/projects/demo")
    assert response.status_code == 201
    project = response.get_json()
    assert project["state"] == "analyzed"
    analysis = client.get(f"/api/projects/{project['id']}/analysis").get_json()
    assert analysis["summary"]["run_count"] == 9
    assert analysis["hypotheses"]


def test_legacy_analysis_summary_is_recomputed_after_schema_migration(tmp_path):
    app = create_app({"TESTING": True, "WORKSPACE_ROOT": tmp_path / "workspace"})
    client = app.test_client()
    project = client.post("/api/projects/demo").get_json()
    workspace = app.extensions["experimentlens_workspace"]
    legacy_summary = workspace.read_json(project["id"], "analysis/summary.json")
    legacy_summary.pop("metric_definitions")
    legacy_summary.pop("metric_summaries")
    legacy_summary.pop("constraints")
    workspace.write_json(project["id"], "analysis/summary.json", legacy_summary)

    response = client.get(f"/api/projects/{project['id']}/analysis")

    assert response.status_code == 200
    summary = response.get_json()["summary"]
    assert summary["metric_definitions"]
    assert summary["metric_summaries"]
    assert "constraints" in summary
