from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from ..domain import SchemaMapping
from ..ingestion import combine_tables, infer_mapping, infer_run_from_text, normalize, parse_file
from ..repositories.interfaces import ExperimentRepository


class IngestionService:
    def __init__(self, repository: ExperimentRepository) -> None:
        self.repository = repository

    def ingest_paths(self, project_id: str, paths: list[Path]) -> dict[str, Any]:
        project = self.repository.get_project(project_id)
        tables: list[pd.DataFrame] = []
        configs: list[dict[str, Any]] = []
        logs: list[dict[str, Any]] = []
        source_summaries = []
        for path in paths:
            parsed = parse_file(path)
            tables.extend(parsed.tables)
            configs.extend(parsed.configs)
            logs.extend(parsed.logs)
            source_summaries.append({
                "name": path.name,
                "type": path.suffix.lower().lstrip("."),
                "rows": sum(len(frame) for frame in parsed.tables),
                "log_lines": len(parsed.logs),
            })
        frame = combine_tables(tables)
        if not frame.empty:
            records = json.loads(frame.to_json(orient="records", force_ascii=False))
            self.repository.write_json(project_id, "scratch/raw_table.json", records)
        existing_configs = self.repository.read_json(project_id, "scratch/configs.json", [])
        existing_logs = self.repository.read_json(project_id, "scratch/logs.json", [])
        self.repository.write_json(project_id, "scratch/configs.json", [*existing_configs, *configs])
        self.repository.write_json(project_id, "scratch/logs.json", [*existing_logs, *logs])
        project.sources.extend(source_summaries)
        project.state = "mapping" if not frame.empty else "awaiting_results"
        self.repository.save_project(project)
        suggestion = None
        confidence = None
        preview: list[dict[str, Any]] = []
        if not frame.empty:
            mapping, confidence = infer_mapping(frame)
            project.mapping = mapping
            self.repository.save_project(project)
            suggestion = mapping.model_dump()
            preview = _clean_records(frame.head(12))
        return {
            "sources": source_summaries,
            "mapping": suggestion,
            "confidence": confidence,
            "preview": preview,
        }

    def confirm_mapping(self, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        project = self.repository.get_project(project_id)
        mapping = SchemaMapping.model_validate(payload)
        records = self.repository.read_json(project_id, "scratch/raw_table.json", [])
        if not records:
            raise ValueError("请先上传实验结果表")
        runs, metrics, params = normalize(pd.DataFrame(records), mapping)
        configs = self.repository.read_json(project_id, "scratch/configs.json", [])
        params = _merge_configs(params, runs, configs)
        logs = self.repository.read_json(project_id, "scratch/logs.json", [])
        known_run_ids = set(runs["run_id"].astype(str))
        for record in logs:
            record["run_id"] = infer_run_from_text(
                f"{record.get('source', '')} {record.get('text', '')}", known_run_ids
            )
        self.repository.write_frame(project_id, "runs", runs)
        self.repository.write_frame(project_id, "metrics", metrics)
        self.repository.write_frame(project_id, "params", params)
        self.repository.write_json(project_id, "normalized/artifacts.json", logs)
        project.mapping = mapping
        project.state = "ready"
        self.repository.save_project(project)
        return {
            "run_count": len(runs),
            "metric_count": len(metrics),
            "parameter_count": len(params),
            "mapping": mapping.model_dump(),
        }


def _merge_configs(
    params: pd.DataFrame, runs: pd.DataFrame, configs: list[dict[str, Any]]
) -> pd.DataFrame:
    records = params.to_dict(orient="records") if not params.empty else []
    known = set(runs["run_id"].astype(str))
    for config in configs:
        run_id = next(
            (str(config[key]) for key in ("run_id", "run", "trial_id") if key in config), None
        )
        if run_id not in known:
            continue
        for key, value in _flatten(config).items():
            if key not in {"run_id", "run", "trial_id", "source"}:
                records.append({
                    "run_id": run_id,
                    "key": key,
                    "value": str(value),
                    "value_type": type(value).__name__,
                })
    return pd.DataFrame(records, columns=["run_id", "key", "value", "value_type"])


def _flatten(payload: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    result = {}
    for key, value in payload.items():
        name = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            result.update(_flatten(value, name))
        elif not isinstance(value, (list, tuple, set)):
            result[name] = value
    return result


def _clean_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return json.loads(frame.where(pd.notna(frame), None).to_json(orient="records", force_ascii=False))
