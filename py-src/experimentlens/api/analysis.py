from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request, send_from_directory

from ..service import ExperimentService
from ..workspace import Workspace

analysis_api = Blueprint("analysis_api", __name__)


def _service() -> ExperimentService:
    return current_app.extensions["experimentlens_service"]


def _workspace() -> Workspace:
    return current_app.extensions["experimentlens_workspace"]


@analysis_api.post("/projects/<project_id>/analysis/run")
def run_analysis(project_id: str):
    return jsonify(_service().run_analysis(project_id))


@analysis_api.get("/projects/<project_id>/analysis/summary")
def get_summary(project_id: str):
    return jsonify(_service().get_analysis(project_id)["summary"])


@analysis_api.get("/projects/<project_id>/analysis")
def get_analysis(project_id: str):
    return jsonify(_service().get_analysis(project_id))


@analysis_api.get("/projects/<project_id>/runs")
def get_runs(project_id: str):
    return jsonify(_service().get_runs(project_id, request.args.get("metric")))


@analysis_api.get("/projects/<project_id>/findings")
def get_findings(project_id: str):
    return jsonify(_service().get_analysis(project_id)["findings"])


@analysis_api.get("/projects/<project_id>/hypotheses")
def get_hypotheses(project_id: str):
    return jsonify(_service().get_analysis(project_id)["hypotheses"])


@analysis_api.get("/projects/<project_id>/proposals")
def get_proposals(project_id: str):
    return jsonify(_service().get_analysis(project_id)["proposals"])


@analysis_api.post("/projects/<project_id>/chat")
def chat(project_id: str):
    payload = request.get_json(silent=True) or {}
    return jsonify(_service().chat(project_id, payload.get("question", "")))


@analysis_api.post("/projects/<project_id>/reports/generate")
def generate_report(project_id: str):
    return jsonify(_service().generate_report(project_id))


@analysis_api.put("/projects/<project_id>/reports/analysis-report")
def save_report(project_id: str):
    payload = request.get_json(silent=True) or {}
    _service().save_report_html(project_id, payload.get("html", ""))
    return jsonify({"saved": True})


@analysis_api.get("/projects/<project_id>/reports/analysis-report.md")
def download_report(project_id: str):
    _service().generate_report(project_id)
    reports = _workspace().project_dir(project_id) / "reports"
    return send_from_directory(
        reports, "analysis-report.md", as_attachment=True,
        download_name="experimentlens-report.md",
    )


@analysis_api.get("/projects/<project_id>/reports/download")
def download_current_report(project_id: str):
    reports = _workspace().project_dir(project_id) / "reports"
    html = reports / "analysis-report.html"
    if html.exists():
        return send_from_directory(
            reports, html.name, as_attachment=True,
            download_name="experimentlens-report.html",
        )
    _service().generate_report(project_id)
    return send_from_directory(
        reports, "analysis-report.md", as_attachment=True,
        download_name="experimentlens-report.md",
    )
