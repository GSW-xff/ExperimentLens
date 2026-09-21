from __future__ import annotations

import pandas as pd
from flask import Blueprint, current_app, jsonify, request

from ..ingestion import infer_mapping
from ..service import ExperimentService
from ..workspace import Workspace

projects_api = Blueprint("projects_api", __name__)


def _service() -> ExperimentService:
    return current_app.extensions["experimentlens_service"]


def _workspace() -> Workspace:
    return current_app.extensions["experimentlens_workspace"]


@projects_api.get("/health")
def health():
    return jsonify({"status": "ok", "version": "0.1.0"})


@projects_api.get("/projects")
def list_projects():
    return jsonify([project.model_dump(mode="json") for project in _workspace().list_projects()])


@projects_api.post("/projects")
def create_project():
    payload = request.get_json(silent=True) or {}
    project = _service().create_project(
        payload.get("name", ""),
        payload.get("objective", ""),
        payload.get("experiment_type", "general"),
    )
    return jsonify(project.model_dump(mode="json")), 201


@projects_api.post("/projects/demo")
def create_demo():
    return jsonify(_service().create_demo().model_dump(mode="json")), 201


@projects_api.get("/projects/<project_id>")
def get_project(project_id: str):
    return jsonify(_workspace().get_project(project_id).model_dump(mode="json"))


@projects_api.post("/projects/<project_id>/sources/upload")
def upload_sources(project_id: str):
    if not request.files:
        raise ValueError("请选择至少一个文件")
    workspace = _workspace()
    workspace.get_project(project_id)
    paths = [
        workspace.save_upload(project_id, uploaded.filename or "upload", uploaded.stream)[0]
        for uploaded in request.files.getlist("files")
    ]
    return jsonify(_service().ingest_paths(project_id, paths))


@projects_api.post("/projects/<project_id>/schema/infer")
def infer_schema(project_id: str):
    records = _workspace().read_json(project_id, "scratch/raw_table.json", [])
    if not records:
        raise ValueError("请先上传实验结果表")
    mapping, confidence = infer_mapping(pd.DataFrame(records))
    return jsonify({"mapping": mapping.model_dump(), "confidence": confidence})


@projects_api.post("/projects/<project_id>/schema/confirm")
def confirm_schema(project_id: str):
    return jsonify(_service().confirm_mapping(project_id, request.get_json(force=True)))
