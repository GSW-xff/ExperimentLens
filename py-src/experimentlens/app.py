from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_from_directory
from pydantic import ValidationError

from .service import ExperimentService
from .workspace import Workspace


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, static_folder=None)
    app.config.update({"MAX_CONTENT_LENGTH": 60 * 1024 * 1024})
    if test_config:
        app.config.update(test_config)
    workspace = Workspace(app.config.get("WORKSPACE_ROOT"))
    service = ExperimentService(workspace)
    app.extensions["experimentlens_service"] = service

    @app.errorhandler(ValueError)
    @app.errorhandler(ValidationError)
    def handle_validation(error):
        return jsonify({"error": str(error)}), 400

    @app.errorhandler(FileNotFoundError)
    def handle_missing(error):
        return jsonify({"error": f"未找到资源：{error}"}), 404

    @app.errorhandler(413)
    def handle_too_large(_error):
        return jsonify({"error": "上传文件过大"}), 413

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "version": "0.1.0"})

    @app.get("/api/projects")
    def list_projects():
        return jsonify([project.model_dump(mode="json") for project in workspace.list_projects()])

    @app.post("/api/projects")
    def create_project():
        payload = request.get_json(silent=True) or {}
        project = service.create_project(payload.get("name", ""), payload.get("objective", ""))
        return jsonify(project.model_dump(mode="json")), 201

    @app.post("/api/projects/demo")
    def create_demo():
        project = service.create_demo()
        return jsonify(project.model_dump(mode="json")), 201

    @app.get("/api/projects/<project_id>")
    def get_project(project_id: str):
        return jsonify(workspace.get_project(project_id).model_dump(mode="json"))

    @app.post("/api/projects/<project_id>/sources/upload")
    def upload_sources(project_id: str):
        if not request.files:
            raise ValueError("请选择至少一个文件")
        paths = []
        workspace.get_project(project_id)
        for uploaded in request.files.getlist("files"):
            path, _digest = workspace.save_upload(project_id, uploaded.filename or "upload", uploaded.stream)
            paths.append(path)
        return jsonify(service.ingest_paths(project_id, paths))

    @app.post("/api/projects/<project_id>/schema/infer")
    def infer_schema(project_id: str):
        records = workspace.read_json(project_id, "scratch/raw_table.json", [])
        if not records:
            raise ValueError("请先上传实验结果表")
        import pandas as pd

        from .ingestion import infer_mapping

        mapping, confidence = infer_mapping(pd.DataFrame(records))
        return jsonify({"mapping": mapping.model_dump(), "confidence": confidence})

    @app.post("/api/projects/<project_id>/schema/confirm")
    def confirm_schema(project_id: str):
        return jsonify(service.confirm_mapping(project_id, request.get_json(force=True)))

    @app.post("/api/projects/<project_id>/analysis/run")
    def run_analysis(project_id: str):
        return jsonify(service.run_analysis(project_id))

    @app.get("/api/projects/<project_id>/analysis/summary")
    def get_summary(project_id: str):
        return jsonify(service.get_analysis(project_id)["summary"])

    @app.get("/api/projects/<project_id>/analysis")
    def get_analysis(project_id: str):
        return jsonify(service.get_analysis(project_id))

    @app.get("/api/projects/<project_id>/runs")
    def get_runs(project_id: str):
        return jsonify(service.get_runs(project_id))

    @app.get("/api/projects/<project_id>/findings")
    def get_findings(project_id: str):
        return jsonify(service.get_analysis(project_id)["findings"])

    @app.get("/api/projects/<project_id>/hypotheses")
    def get_hypotheses(project_id: str):
        return jsonify(service.get_analysis(project_id)["hypotheses"])

    @app.get("/api/projects/<project_id>/proposals")
    def get_proposals(project_id: str):
        return jsonify(service.get_analysis(project_id)["proposals"])

    @app.post("/api/projects/<project_id>/chat")
    def chat(project_id: str):
        payload = request.get_json(silent=True) or {}
        return jsonify(service.chat(project_id, payload.get("question", "")))

    @app.post("/api/projects/<project_id>/reports/generate")
    def generate_report(project_id: str):
        return jsonify(service.generate_report(project_id))

    @app.put("/api/projects/<project_id>/reports/analysis-report")
    def save_report(project_id: str):
        payload = request.get_json(silent=True) or {}
        service.save_report_html(project_id, payload.get("html", ""))
        return jsonify({"saved": True})

    @app.get("/api/projects/<project_id>/reports/analysis-report.md")
    def download_report(project_id: str):
        service.generate_report(project_id)
        reports = workspace.project_dir(project_id) / "reports"
        return send_from_directory(reports, "analysis-report.md", as_attachment=True, download_name="experimentlens-report.md")

    @app.get("/api/projects/<project_id>/reports/download")
    def download_current_report(project_id: str):
        reports = workspace.project_dir(project_id) / "reports"
        html = reports / "analysis-report.html"
        if html.exists():
            return send_from_directory(
                reports,
                html.name,
                as_attachment=True,
                download_name="experimentlens-report.html",
            )
        service.generate_report(project_id)
        return send_from_directory(
            reports,
            "analysis-report.md",
            as_attachment=True,
            download_name="experimentlens-report.md",
        )

    frontend = Path(app.config.get("FRONTEND_DIST") or Path(__file__).parents[2] / "dist")

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def frontend_app(path: str):
        target = frontend / path
        if path and target.is_file():
            return send_from_directory(frontend, path)
        index = frontend / "index.html"
        if index.exists():
            return send_from_directory(frontend, "index.html")
        return Response("ExperimentLens API is running. Start the Vite development server for the web interface.", mimetype="text/plain")

    return app


def main() -> None:
    app = create_app()
    app.run(host=os.environ.get("EXPERIMENTLENS_HOST", "127.0.0.1"), port=int(os.environ.get("EXPERIMENTLENS_PORT", "5050")), debug=os.environ.get("FLASK_DEBUG") == "1")


if __name__ == "__main__":
    main()
