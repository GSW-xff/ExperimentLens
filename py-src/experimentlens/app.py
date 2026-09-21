from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, Response, jsonify, send_from_directory
from pydantic import ValidationError

from .api import analysis_api, projects_api
from .repositories.local import LocalRepository
from .service import ExperimentService


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, static_folder=None)
    app.config.update({"MAX_CONTENT_LENGTH": 60 * 1024 * 1024})
    if test_config:
        app.config.update(test_config)

    workspace = LocalRepository(app.config.get("WORKSPACE_ROOT"))
    app.extensions["experimentlens_workspace"] = workspace
    app.extensions["experimentlens_service"] = ExperimentService(workspace)
    app.register_blueprint(projects_api, url_prefix="/api")
    app.register_blueprint(analysis_api, url_prefix="/api")

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

    frontend = Path(app.config.get("FRONTEND_DIST") or Path(__file__).parents[2] / "dist")

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def frontend_app(path: str):
        target = frontend / path
        if path and target.is_file():
            return send_from_directory(frontend, path)
        if (frontend / "index.html").exists():
            return send_from_directory(frontend, "index.html")
        return Response(
            "ExperimentLens API is running. Start the Vite development server for the web interface.",
            mimetype="text/plain",
        )

    return app


def main() -> None:
    app = create_app()
    app.run(
        host=os.environ.get("EXPERIMENTLENS_HOST", "127.0.0.1"),
        port=int(os.environ.get("EXPERIMENTLENS_PORT", "5050")),
        debug=os.environ.get("FLASK_DEBUG") == "1",
    )


if __name__ == "__main__":
    main()
