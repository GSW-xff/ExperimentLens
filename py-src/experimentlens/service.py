"""Backward-compatible service facade.

Use-case implementations live in :mod:`experimentlens.services`; this module keeps
the MVP import and API contract stable while routes migrate incrementally.
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

import pandas as pd

from .domain import Project
from .ingestion import infer_mapping
from .repositories.interfaces import ExperimentRepository
from .services import AnalysisService, IngestionService, ProjectService, ReportService
from .services.report import render_report


class ExperimentService:
    def __init__(self, workspace: ExperimentRepository):
        self.workspace = workspace
        self.projects = ProjectService(workspace)
        self.ingestion = IngestionService(workspace)
        self.analysis = AnalysisService(workspace)
        self.reports = ReportService(workspace, self.analysis)

    def create_project(self, name: str, objective: str) -> Project:
        return self.projects.create_project(name, objective)

    def ingest_paths(self, project_id: str, paths: list[Path]) -> dict[str, Any]:
        return self.ingestion.ingest_paths(project_id, paths)

    def confirm_mapping(self, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.ingestion.confirm_mapping(project_id, payload)

    def run_analysis(self, project_id: str) -> dict[str, Any]:
        return self.analysis.run_analysis(project_id)

    def get_analysis(self, project_id: str) -> dict[str, Any]:
        return self.analysis.get_analysis(project_id)

    def get_runs(self, project_id: str) -> list[dict[str, Any]]:
        return self.analysis.get_runs(project_id)

    def chat(self, project_id: str, question: str) -> dict[str, Any]:
        return self.analysis.chat(project_id, question)

    def generate_report(self, project_id: str) -> dict[str, str]:
        return self.reports.generate_report(project_id)

    def save_report_html(self, project_id: str, html: str) -> Path:
        return self.reports.save_report_html(project_id, html)

    def create_demo(self) -> Project:
        project = self.create_project(
            "Transformer 调参实验",
            "在不显著增加训练成本的前提下，提高验证集准确率并保持多 seed 稳定性。",
        )
        csv_text = """run_id,group,seed,status,accuracy,train_loss,duration_seconds,batch_size,learning_rate,dataset_version
base-17,Baseline,17,completed,0.842,0.382,3520,32,0.0003,v3
base-29,Baseline,29,completed,0.848,0.371,3490,32,0.0003,v3
base-43,Baseline,43,completed,0.845,0.376,3552,32,0.0003,v3
cos-17,Cosine LR,17,completed,0.865,0.341,3690,32,0.0003,v3
cos-29,Cosine LR,29,completed,0.861,0.349,3714,32,0.0003,v3
cos-43,Cosine LR,43,completed,0.867,0.337,3688,32,0.0003,v3
large-17,Large Batch,17,completed,0.871,0.332,3050,64,0.0003,v3
large-29,Large Batch,29,failed,,0.000,1810,64,0.0003,v3
large-43,Large Batch,43,completed,0.829,0.415,3095,64,0.0003,v3
"""
        frame = pd.read_csv(io.StringIO(csv_text))
        records = json.loads(frame.to_json(orient="records"))
        self.workspace.write_json(project.id, "scratch/raw_table.json", records)
        logs = [
            {
                "source": "large-29.log",
                "line": 148,
                "text": "RuntimeError: CUDA out of memory. Tried to allocate 1.50 GiB",
                "run_id": "large-29",
            },
            {
                "source": "large-43.log",
                "line": 102,
                "text": "warning: validation accuracy oscillation detected",
                "run_id": "large-43",
            },
        ]
        self.workspace.write_json(project.id, "scratch/logs.json", logs)
        project.sources = [
            {"name": "results.csv", "type": "csv", "rows": 9, "log_lines": 0},
            {"name": "large-29.log", "type": "log", "rows": 0, "log_lines": 1},
        ]
        mapping, _ = infer_mapping(frame)
        project.mapping = mapping
        self.workspace.save_project(project)
        self.confirm_mapping(project.id, mapping.model_dump())
        self.run_analysis(project.id)
        return self.workspace.get_project(project.id)


__all__ = ["ExperimentService", "render_report"]
