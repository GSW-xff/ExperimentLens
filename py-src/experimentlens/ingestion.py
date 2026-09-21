from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from .domain import MetricDefinition, MetricDirection, MetricRole, SchemaMapping

RUN_ALIASES = ("run_id", "run", "trial_id", "trial", "experiment_id", "id")
GROUP_ALIASES = ("group", "variant", "arm", "config_name", "experiment_group", "model")
SEED_ALIASES = ("seed", "random_seed", "rng_seed")
STATUS_ALIASES = ("status", "state", "result")
DURATION_ALIASES = ("duration_seconds", "duration", "elapsed_seconds", "runtime_seconds")
METRIC_HINTS = (
    "accuracy",
    "acc",
    "f1",
    "auc",
    "precision",
    "recall",
    "loss",
    "score",
    "bleu",
    "rouge",
    "perplexity",
    "iou",
    "mae",
    "rmse",
    "reward",
    "latency",
    "throughput",
    "memory",
    "cost",
)
SUPPORTED_EXTENSIONS = {".csv", ".tsv", ".xlsx", ".xls", ".json", ".jsonl", ".yaml", ".yml", ".txt", ".log"}


@dataclass
class ParsedBundle:
    tables: list[pd.DataFrame]
    configs: list[dict[str, Any]]
    logs: list[dict[str, Any]]


def parse_file(path: Path) -> ParsedBundle:
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"不支持的文件类型：{suffix or 'unknown'}")
    if path.stat().st_size > 50 * 1024 * 1024:
        raise ValueError("单个文件不能超过 50 MB")

    if suffix == ".csv":
        return ParsedBundle([pd.read_csv(path)], [], [])
    if suffix == ".tsv":
        return ParsedBundle([pd.read_csv(path, sep="\t")], [], [])
    if suffix in {".xlsx", ".xls"}:
        sheets = pd.read_excel(path, sheet_name=None)
        return ParsedBundle([frame for frame in sheets.values() if not frame.empty], [], [])
    if suffix in {".yaml", ".yml"}:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        return _structured_payload(payload, path.name)
    if suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        return _structured_payload(payload, path.name)
    if suffix == ".jsonl":
        records: list[dict[str, Any]] = []
        text_lines: list[str] = []
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                value = json.loads(line)
                if isinstance(value, dict):
                    records.append(value)
            except json.JSONDecodeError:
                text_lines.append(line)
        if records and _looks_tabular(records):
            return ParsedBundle([pd.json_normalize(records)], [], _extract_log_records(text_lines, path.name))
        return ParsedBundle([], records, _extract_log_records(text_lines, path.name))
    return ParsedBundle([], [], _extract_log_records(path.read_text(encoding="utf-8", errors="replace").splitlines(), path.name))


def _structured_payload(payload: Any, filename: str) -> ParsedBundle:
    if isinstance(payload, list) and payload and all(isinstance(row, dict) for row in payload):
        if _looks_tabular(payload):
            return ParsedBundle([pd.json_normalize(payload)], [], [])
        return ParsedBundle([], payload, [])
    if isinstance(payload, dict):
        for key in ("runs", "results", "experiments", "trials", "data"):
            records = payload.get(key)
            if isinstance(records, list) and records and all(isinstance(row, dict) for row in records):
                return ParsedBundle([pd.json_normalize(records)], [{"source": filename, **payload}], [])
        return ParsedBundle([], [{"source": filename, **payload}], [])
    raise ValueError(f"{filename} 中没有可识别的结构化数据")


def _looks_tabular(records: list[dict[str, Any]]) -> bool:
    if not records:
        return False
    common = set(records[0])
    for record in records[1:5]:
        common &= set(record)
    return bool(common & set(RUN_ALIASES + GROUP_ALIASES + METRIC_HINTS))


def _extract_log_records(lines: list[str], filename: str) -> list[dict[str, Any]]:
    records = []
    for index, line in enumerate(lines, start=1):
        if line.strip():
            records.append({"source": filename, "line": index, "text": line[:4000]})
    return records


def combine_tables(tables: list[pd.DataFrame]) -> pd.DataFrame:
    usable = [frame.copy() for frame in tables if not frame.empty]
    if not usable:
        return pd.DataFrame()
    columns = [set(str(column) for column in frame.columns) for frame in usable]
    anchor = max(range(len(usable)), key=lambda index: len(columns[index]))
    compatible = [
        frame for index, frame in enumerate(usable)
        if index == anchor or len(columns[anchor] & columns[index]) >= min(2, len(columns[index]))
    ]
    normalized = []
    for frame in compatible:
        frame.columns = [str(column).strip() for column in frame.columns]
        normalized.append(frame)
    return pd.concat(normalized, ignore_index=True, sort=False)


def infer_mapping(frame: pd.DataFrame) -> tuple[SchemaMapping, dict[str, float]]:
    if frame.empty:
        raise ValueError("未找到包含实验结果的表格")
    columns = [str(column) for column in frame.columns]
    lowered = {column.lower().strip(): column for column in columns}

    def choose(aliases: tuple[str, ...], fallback: str | None = None) -> str | None:
        for alias in aliases:
            if alias in lowered:
                return lowered[alias]
        return fallback

    numeric_columns = [
        column for column in columns
        if pd.to_numeric(frame[column], errors="coerce").notna().mean() >= 0.7
    ]
    metric_columns = [
        column for column in numeric_columns
        if any(hint in column.lower() for hint in METRIC_HINTS)
    ]
    excluded = set(filter(None, [choose(SEED_ALIASES), choose(DURATION_ALIASES)]))
    if not metric_columns:
        metric_columns = [column for column in numeric_columns if column not in excluded]
    if not metric_columns:
        raise ValueError("未识别到数值指标列")
    primary = metric_columns[0]
    group_column = choose(GROUP_ALIASES)
    if not group_column:
        candidates = [column for column in columns if frame[column].nunique(dropna=True) <= max(12, len(frame) // 2)]
        group_column = candidates[0] if candidates else columns[0]
    run_column = choose(RUN_ALIASES)
    if not run_column:
        frame["run_id"] = [f"run-{index + 1:03d}" for index in range(len(frame))]
        run_column = "run_id"

    groups = [str(value) for value in frame[group_column].dropna().unique()]
    baseline = next((value for value in groups if "base" in value.lower() or value.lower() in {"a", "control"}), groups[0])
    direction = _metric_direction(primary)
    structural = set(filter(None, [run_column, group_column, choose(SEED_ALIASES), choose(STATUS_ALIASES), choose(DURATION_ALIASES)]))
    parameter_columns = [column for column in columns if column not in structural and column not in metric_columns]
    mapping = SchemaMapping(
        run_id=run_column,
        group=group_column,
        seed=choose(SEED_ALIASES),
        status=choose(STATUS_ALIASES),
        duration=choose(DURATION_ALIASES),
        primary_metric=primary,
        metric_direction=direction,
        baseline_group=baseline,
        metric_columns=metric_columns,
        metric_definitions=[
            MetricDefinition(
                key=column,
                display_name=column,
                role=(
                    MetricRole.PRIMARY
                    if column == primary
                    else MetricRole.RESOURCE
                    if any(word in column.lower() for word in ("latency", "memory", "cost", "duration"))
                    else MetricRole.SECONDARY
                ),
                direction=MetricDirection(_metric_direction(column)),
            )
            for column in metric_columns
        ],
        parameter_columns=parameter_columns,
    )
    confidence = {
        "run_id": 0.96 if run_column.lower() in RUN_ALIASES else 0.72,
        "group": 0.94 if group_column.lower() in GROUP_ALIASES else 0.68,
        "seed": 0.95 if mapping.seed else 0.2,
        "primary_metric": 0.9 if any(hint in primary.lower() for hint in METRIC_HINTS) else 0.66,
    }
    return mapping, confidence


def _metric_direction(column: str) -> str:
    return (
        "minimize"
        if any(
            word in column.lower()
            for word in ("loss", "error", "mae", "rmse", "perplexity", "latency", "memory", "cost")
        )
        else "maximize"
    )


def normalize(frame: pd.DataFrame, mapping: SchemaMapping) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    required = {mapping.run_id, mapping.group, mapping.primary_metric}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"映射字段不存在：{', '.join(sorted(missing))}")
    source = frame.copy().replace({np.nan: None})
    run_ids = source[mapping.run_id].astype(str)
    runs = pd.DataFrame({
        "run_id": run_ids,
        "experiment_id": "default",
        "group": source[mapping.group].astype(str),
        "seed": source[mapping.seed] if mapping.seed else None,
        "status": source[mapping.status].fillna("completed").astype(str) if mapping.status else "completed",
        "duration_seconds": pd.to_numeric(source[mapping.duration], errors="coerce") if mapping.duration else None,
        "source_type": "file",
        "source_run_id": run_ids,
    })
    metric_frames = []
    for column in dict.fromkeys([*mapping.metric_columns, mapping.primary_metric]):
        if column not in source:
            continue
        metric_frames.append(pd.DataFrame({
            "run_id": run_ids,
            "key": column,
            "value": pd.to_numeric(source[column], errors="coerce"),
            "step": None,
            "timestamp": None,
            "split": _infer_split(column),
        }))
    metrics = pd.concat(metric_frames, ignore_index=True) if metric_frames else pd.DataFrame()
    parameter_records = []
    for column in mapping.parameter_columns:
        if column not in source:
            continue
        for run_id, value in zip(run_ids, source[column], strict=False):
            if value is not None:
                parameter_records.append({
                    "run_id": run_id,
                    "key": column,
                    "value": str(value),
                    "value_type": type(value).__name__,
                })
    params = pd.DataFrame(parameter_records, columns=["run_id", "key", "value", "value_type"])
    return runs, metrics, params


def _infer_split(column: str) -> str | None:
    name = column.lower()
    if "val" in name or "valid" in name:
        return "validation"
    if "train" in name:
        return "train"
    if "test" in name:
        return "test"
    return None


def infer_run_from_text(text: str, known_run_ids: set[str]) -> str | None:
    for run_id in sorted(known_run_ids, key=len, reverse=True):
        if run_id in text:
            return run_id
    match = re.search(r"(?:run|trial)[_ :=-]*([A-Za-z0-9_.-]+)", text, re.IGNORECASE)
    return match.group(1) if match else None
