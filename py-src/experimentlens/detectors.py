from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .domain import EvidenceRef, Finding, SchemaMapping, Severity


@dataclass(frozen=True)
class DetectorContext:
    data: pd.DataFrame
    params: pd.DataFrame
    logs: list[dict[str, Any]]
    mapping: SchemaMapping
    groups: list[dict[str, Any]]


Detector = Callable[[DetectorContext], list[Finding]]
DETECTOR_REGISTRY: dict[str, Detector] = {}


def register_detector(name: str) -> Callable[[Detector], Detector]:
    def decorator(detector: Detector) -> Detector:
        if name in DETECTOR_REGISTRY:
            raise ValueError(f"detector already registered: {name}")
        DETECTOR_REGISTRY[name] = detector
        return detector

    return decorator


def run_detectors(
    data: pd.DataFrame,
    params: pd.DataFrame,
    logs: list[dict[str, Any]],
    mapping: SchemaMapping,
    groups: list[dict[str, Any]],
) -> list[Finding]:
    context = DetectorContext(data, params, logs, mapping, groups)
    findings = [finding for detector in DETECTOR_REGISTRY.values() for finding in detector(context)]
    return _deduplicate(findings)


@register_detector("run_integrity")
def detect_run_integrity(context: DetectorContext) -> list[Finding]:
    findings: list[Finding] = []
    failed = context.data[
        context.data["status"].astype(str).str.lower().isin({"failed", "error", "crashed", "oom"})
    ]
    for row in failed.itertuples():
        findings.append(_finding(
            "failed_run", Severity.CRITICAL, f"运行 {row.run_id} 未完成",
            f"状态记录为 {row.status}，该运行未参与主要指标比较。",
            [_evidence("run", str(row.run_id), f"{row.run_id} · {row.status}")], 0.99,
        ))
    invalid = context.data[
        context.data["value"].isna()
        | ~np.isfinite(pd.to_numeric(context.data["value"], errors="coerce"))
    ]
    for row in invalid.itertuples():
        findings.append(_finding(
            "invalid_metric", Severity.CRITICAL,
            f"{row.run_id} 的 {context.mapping.primary_metric} 无效",
            "主指标缺失、NaN 或 Inf，无法进入统计比较。",
            [_evidence(
                "metric",
                f"{row.run_id}:{context.mapping.primary_metric}",
                f"{row.run_id} · {context.mapping.primary_metric}",
            )],
            1.0,
        ))
    duplicated = context.data[context.data["run_id"].duplicated(keep=False)]
    for run_id in duplicated["run_id"].astype(str).unique():
        findings.append(_finding(
            "duplicate_run", Severity.WARNING, f"检测到重复运行 {run_id}",
            "同一 run ID 出现多次，可能会让汇总结果被重复计权。",
            [_evidence("run", run_id, run_id)], 1.0,
        ))
    if "seed" in context.data and context.data["seed"].isna().any():
        rows = context.data[context.data["seed"].isna()]
        findings.append(_finding(
            "missing_seed", Severity.INFO, "部分运行缺少 seed",
            f"{len(rows)} 个运行没有 seed，复现实验和稳定性解释会受到限制。",
            [_evidence("run", str(run_id), str(run_id)) for run_id in rows["run_id"].head(5)],
            1.0,
        ))
    return findings


@register_detector("metric_outlier")
def detect_metric_outliers(context: DetectorContext) -> list[Finding]:
    findings: list[Finding] = []
    for group, frame in context.data.groupby("group"):
        valid = frame["value"].dropna().astype(float)
        if len(valid) < 4:
            continue
        median = float(valid.median())
        mad = float(np.median(np.abs(valid - median)))
        if mad <= 0:
            continue
        robust_z = 0.6745 * (valid - median) / mad
        for index in robust_z[robust_z.abs() > 3.5].index:
            row = context.data.loc[index]
            findings.append(_finding(
                "metric_outlier", Severity.WARNING, f"{row.run_id} 是组内离群点",
                f"{context.mapping.primary_metric}={row.value:.4g}，明显偏离 {group} 组的中位数 {median:.4g}。",
                [_evidence(
                    "metric",
                    f"{row.run_id}:{context.mapping.primary_metric}",
                    f"{row.run_id} · {context.mapping.primary_metric}={row.value:.4g}",
                )],
                0.92,
            ))
    return findings


@register_detector("seed_instability")
def detect_seed_instability(context: DetectorContext) -> list[Finding]:
    baseline_std = next(
        (item["std"] for item in context.groups if item["group"] == context.mapping.baseline_group),
        None,
    )
    if not baseline_std:
        return []
    return [
        _finding(
            "seed_instability", Severity.WARNING, f"{item['group']} 的 seed 波动增大",
            f"标准差 {item['std']:.4g}，约为 baseline 的 {item['std'] / baseline_std:.1f} 倍。",
            [_evidence("run", run_id, run_id) for run_id in item["run_ids"]], 0.88,
        )
        for item in context.groups
        if item["n"] >= 3 and item["std"] and item["std"] > baseline_std * 1.8
    ]


@register_detector("dataset_drift")
def detect_dataset_drift(context: DetectorContext) -> list[Finding]:
    if context.params.empty:
        return []
    grouped_params = context.params.groupby("key")["value"].nunique()
    if grouped_params.get("dataset_version", 0) <= 1:
        return []
    relevant = context.params[context.params["key"] == "dataset_version"]
    return [_finding(
        "dataset_drift", Severity.WARNING, "实验使用了不同的数据版本",
        "dataset_version 在运行之间不一致，对比可能混入数据差异。",
        [
            _evidence("param", f"{row.run_id}:dataset_version", f"{row.run_id} · {row.value}")
            for row in relevant.itertuples()
        ],
        0.98,
    )]


ERROR_PATTERNS = {
    "out_of_memory": re.compile(r"out of memory|\boom\b|cuda.*memory", re.IGNORECASE),
    "numerical_error": re.compile(r"nan|inf|overflow|underflow|numerical", re.IGNORECASE),
    "exception": re.compile(r"traceback|exception|error:|failed", re.IGNORECASE),
}


@register_detector("log_errors")
def detect_log_errors(context: DetectorContext) -> list[Finding]:
    findings: list[Finding] = []
    for record in context.logs:
        text = str(record.get("text", ""))
        for kind, pattern in ERROR_PATTERNS.items():
            if not pattern.search(text):
                continue
            severity = Severity.CRITICAL if kind in {"out_of_memory", "numerical_error"} else Severity.WARNING
            source = record.get("source", "log")
            line = record.get("line", "?")
            findings.append(_finding(
                f"log_{kind}", severity, _log_title(kind), text[:240],
                [_evidence("log", f"{source}:{line}", f"{source} 第 {line} 行", text[:300])],
                0.95,
            ))
            break
    return findings


def _finding(
    kind: str,
    severity: Severity,
    title: str,
    description: str,
    evidence: list[EvidenceRef],
    confidence: float,
) -> Finding:
    suffix = evidence[0].id.replace(":", "_") if evidence else str(abs(hash(title)))
    return Finding(
        id=f"finding_{kind}_{suffix}",
        type=kind,
        severity=severity,
        title=title,
        description=description,
        evidence_refs=evidence,
        detector=f"rules.{kind}",
        confidence=confidence,
    )


def _evidence(kind: str, identifier: str, label: str, detail: str | None = None) -> EvidenceRef:
    return EvidenceRef(id=identifier, kind=kind, label=label, detail=detail)


def _deduplicate(findings: list[Finding]) -> list[Finding]:
    result = []
    seen = set()
    for finding in findings:
        key = (finding.type, tuple(ref.id for ref in finding.evidence_refs))
        if key not in seen:
            seen.add(key)
            result.append(finding)
    return result


def _log_title(kind: str) -> str:
    return {
        "out_of_memory": "日志中发现显存不足",
        "numerical_error": "日志中发现数值异常",
        "exception": "日志中发现运行异常",
    }[kind]
