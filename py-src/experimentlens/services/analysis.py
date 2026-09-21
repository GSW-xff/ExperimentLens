from __future__ import annotations

from typing import Any

import pandas as pd

from ..analysis import analyze, answer_question
from ..repositories.interfaces import ExperimentRepository


class AnalysisService:
    def __init__(self, repository: ExperimentRepository) -> None:
        self.repository = repository

    def run_analysis(self, project_id: str) -> dict[str, Any]:
        project = self.repository.get_project(project_id)
        if not project.mapping:
            raise ValueError("请先确认字段映射")
        result = analyze(
            self.repository.read_frame(project_id, "runs"),
            self.repository.read_frame(project_id, "metrics"),
            self.repository.read_frame(project_id, "params"),
            self.repository.read_json(project_id, "normalized/artifacts.json", []),
            project.mapping,
        )
        for name in ("summary", "findings", "hypotheses", "proposals"):
            self.repository.write_json(project_id, f"analysis/{name}.json", result[name])
        project.state = "analyzed"
        self.repository.save_project(project)
        return result

    def get_analysis(self, project_id: str) -> dict[str, Any]:
        summary = self.repository.read_json(project_id, "analysis/summary.json")
        if summary is None:
            return self.run_analysis(project_id)
        return {
            "summary": summary,
            "findings": self.repository.read_json(project_id, "analysis/findings.json", []),
            "hypotheses": self.repository.read_json(project_id, "analysis/hypotheses.json", []),
            "proposals": self.repository.read_json(project_id, "analysis/proposals.json", []),
        }

    def get_runs(self, project_id: str, metric_key: str | None = None) -> list[dict[str, Any]]:
        project = self.repository.get_project(project_id)
        runs = self.repository.read_frame(project_id, "runs")
        metrics = self.repository.read_frame(project_id, "metrics")
        params = self.repository.read_frame(project_id, "params")
        if runs.empty:
            return []
        metric_key = metric_key or (project.mapping.primary_metric if project.mapping else None)
        if project.mapping and metric_key not in project.mapping.metric_columns:
            raise ValueError(f"未知指标：{metric_key}")
        primary = (
            metrics[metrics["key"] == metric_key][["run_id", "value"]]
            if metric_key and not metrics.empty
            else pd.DataFrame(columns=["run_id", "value"])
        )
        wide = runs.merge(primary.rename(columns={"value": "metric_value"}), on="run_id", how="left")
        params_by_run: dict[str, dict[str, str]] = {}
        for row in params.itertuples():
            params_by_run.setdefault(str(row.run_id), {})[str(row.key)] = str(row.value)
        result = []
        for row in wide.to_dict(orient="records"):
            cleaned = {key: (None if pd.isna(value) else value) for key, value in row.items()}
            cleaned["params"] = params_by_run.get(str(cleaned["run_id"]), {})
            cleaned["metric_key"] = metric_key
            result.append(cleaned)
        return result

    def chat(self, project_id: str, question: str) -> dict[str, Any]:
        if not question.strip():
            raise ValueError("问题不能为空")
        return answer_question(question, self.get_analysis(project_id))
