from __future__ import annotations

import math
from statistics import NormalDist
from typing import Any

import numpy as np
import pandas as pd

from .detectors import run_detectors
from .domain import EvidenceRef, ExperimentProposal, Finding, Hypothesis, SchemaMapping, Severity
from .evidence_validator import EvidenceValidator

# Compatibility export for callers that imported the MVP detector entry point.
detect_findings = run_detectors


def analyze(
    runs: pd.DataFrame,
    metrics: pd.DataFrame,
    params: pd.DataFrame,
    logs: list[dict[str, Any]],
    mapping: SchemaMapping,
) -> dict[str, Any]:
    primary = metrics.loc[metrics["key"] == mapping.primary_metric, ["run_id", "value"]].copy()
    primary["value"] = pd.to_numeric(primary["value"], errors="coerce")
    data = runs.merge(primary, on="run_id", how="left")
    data["group"] = data["group"].astype(str)
    groups = _group_statistics(data)
    comparison = _baseline_comparison(data, mapping)
    findings = run_detectors(data, params, logs, mapping, groups)
    hypotheses = generate_hypotheses(findings, mapping)
    EvidenceValidator(runs, metrics, params, logs).validate_analysis(findings, hypotheses)
    proposals = generate_proposals(hypotheses, mapping)
    valid = data["value"].dropna()
    best_row = None
    if not valid.empty:
        index = valid.idxmax() if mapping.metric_direction == "maximize" else valid.idxmin()
        row = data.loc[index]
        best_row = {"run_id": row["run_id"], "group": row["group"], "value": float(row["value"])}
    summary = {
        "primary_metric": mapping.primary_metric,
        "metric_direction": mapping.metric_direction,
        "baseline_group": mapping.baseline_group,
        "run_count": int(len(runs)),
        "successful_runs": int(runs["status"].astype(str).str.lower().isin({"completed", "success", "finished", "ok"}).sum()),
        "failed_runs": int(runs["status"].astype(str).str.lower().isin({"failed", "error", "crashed", "oom"}).sum()),
        "group_count": int(runs["group"].nunique()),
        "best_run": best_row,
        "groups": groups,
        "comparison": comparison,
        "findings_count": len(findings),
        "high_priority_findings": sum(item.severity in {Severity.CRITICAL, Severity.WARNING} for item in findings),
        "conclusion": _conclusion(comparison, mapping),
    }
    return {
        "summary": summary,
        "findings": [item.model_dump(mode="json") for item in findings],
        "hypotheses": [item.model_dump(mode="json") for item in hypotheses],
        "proposals": [item.model_dump(mode="json") for item in proposals],
    }


def _group_statistics(data: pd.DataFrame) -> list[dict[str, Any]]:
    result = []
    for group, frame in data.groupby("group", sort=True):
        values = frame["value"].dropna().astype(float).to_numpy()
        if not len(values):
            result.append({"group": group, "n": 0, "mean": None, "std": None, "ci_low": None, "ci_high": None, "values": []})
            continue
        mean = float(values.mean())
        std = float(values.std(ddof=1)) if len(values) > 1 else 0.0
        margin = 1.96 * std / math.sqrt(len(values)) if len(values) > 1 else 0.0
        result.append({
            "group": group,
            "n": int(len(values)),
            "mean": mean,
            "median": float(np.median(values)),
            "std": std,
            "ci_low": mean - margin,
            "ci_high": mean + margin,
            "values": values.tolist(),
            "run_ids": frame.loc[frame["value"].notna(), "run_id"].astype(str).tolist(),
            "mean_duration": _safe_mean(frame.get("duration_seconds")),
        })
    return result


def _baseline_comparison(data: pd.DataFrame, mapping: SchemaMapping) -> list[dict[str, Any]]:
    baseline = data.loc[data["group"] == mapping.baseline_group, "value"].dropna().astype(float).to_numpy()
    comparisons = []
    if not len(baseline):
        return comparisons
    for group, frame in data.groupby("group", sort=True):
        if group == mapping.baseline_group:
            continue
        candidate = frame["value"].dropna().astype(float).to_numpy()
        if not len(candidate):
            continue
        delta = float(candidate.mean() - baseline.mean())
        pooled_denominator = len(baseline) + len(candidate) - 2
        pooled_variance = (
            ((len(baseline) - 1) * baseline.var(ddof=1) + (len(candidate) - 1) * candidate.var(ddof=1)) / pooled_denominator
            if pooled_denominator > 0 and len(baseline) > 1 and len(candidate) > 1 else 0
        )
        effect = delta / math.sqrt(pooled_variance) if pooled_variance > 0 else 0.0
        se = math.sqrt(
            (baseline.var(ddof=1) / len(baseline) if len(baseline) > 1 else 0)
            + (candidate.var(ddof=1) / len(candidate) if len(candidate) > 1 else 0)
        )
        z_score = delta / se if se else 0
        p_value = 2 * (1 - NormalDist().cdf(abs(z_score))) if se else 1.0
        relative = delta / abs(float(baseline.mean())) if baseline.mean() else None
        comparisons.append({
            "group": str(group),
            "baseline_group": mapping.baseline_group,
            "mean_delta": delta,
            "relative_delta": relative,
            "confidence_interval": [delta - 1.96 * se, delta + 1.96 * se],
            "effect_size": float(effect),
            "p_value_approx": float(p_value),
            "sample_size": {"baseline": int(len(baseline)), "candidate": int(len(candidate))},
            "warnings": ["sample_size_small"] if min(len(baseline), len(candidate)) < 5 else [],
            "evidence_refs": [
                *[f"run:{value}" for value in data.loc[data["group"] == mapping.baseline_group, "run_id"].astype(str)],
                *[f"run:{value}" for value in frame["run_id"].astype(str)],
            ],
        })
    return comparisons


def generate_hypotheses(findings: list[Finding], mapping: SchemaMapping) -> list[Hypothesis]:
    hypotheses: list[Hypothesis] = []
    by_type: dict[str, list[Finding]] = {}
    for finding in findings:
        by_type.setdefault(finding.type, []).append(finding)

    if by_type.keys() & {"log_out_of_memory", "failed_run"}:
        sources = by_type.get("log_out_of_memory", []) + by_type.get("failed_run", [])
        hypotheses.append(Hypothesis(
            id="hyp_memory_pressure",
            description="资源峰值可能导致部分运行失败，并间接造成结果缺失或偏差。",
            supporting_evidence=_collect_evidence(sources),
            contradicting_evidence=[],
            uncertainties=["尚未获得逐步显存曲线", "失败运行是否使用相同 batch size 尚待确认"],
            confidence=0.78 if by_type.get("log_out_of_memory") else 0.56,
            verification_plan="固定数据、模型与 seed，仅降低 batch size 后复跑失败运行，并记录峰值显存。",
        ))
    if by_type.keys() & {"metric_outlier", "seed_instability"}:
        sources = by_type.get("metric_outlier", []) + by_type.get("seed_instability", [])
        hypotheses.append(Hypothesis(
            id="hyp_seed_sensitivity",
            description="候选配置可能对随机初始化或数据顺序敏感，均值提升并不稳定。",
            supporting_evidence=_collect_evidence(sources),
            contradicting_evidence=[],
            uncertainties=["当前 seed 数量较少", "尚未分离初始化与采样顺序的影响"],
            confidence=0.74,
            verification_plan="在完全相同配置下补充 3 个预先指定 seed，比较置信区间与最差分位数。",
        ))
    if by_type.get("dataset_drift"):
        hypotheses.append(Hypothesis(
            id="hyp_dataset_mismatch",
            description="观察到的组间差异可能部分来自数据版本不一致，而非配置本身。",
            supporting_evidence=_collect_evidence(by_type["dataset_drift"]),
            contradicting_evidence=[],
            uncertainties=["尚未核对数据内容哈希"],
            confidence=0.86,
            verification_plan="将 baseline 与候选配置都固定到同一数据版本，使用同一组 seed 进行配对复跑。",
        ))
    if by_type.get("log_numerical_error") or by_type.get("invalid_metric"):
        sources = by_type.get("log_numerical_error", []) + by_type.get("invalid_metric", [])
        hypotheses.append(Hypothesis(
            id="hyp_numerical_instability",
            description="训练过程可能存在数值不稳定，导致无效指标或异常终止。",
            supporting_evidence=_collect_evidence(sources),
            contradicting_evidence=[],
            uncertainties=["缺少梯度范数和 loss scale 轨迹"],
            confidence=0.82,
            verification_plan="保持其余条件不变，启用梯度裁剪与数值监控，复跑同一 seed。",
        ))
    if not hypotheses:
        hypotheses.append(Hypothesis(
            id="hyp_insufficient_evidence",
            description="当前没有足够证据支持明确的故障原因。",
            supporting_evidence=[],
            contradicting_evidence=[],
            uncertainties=["需要更多 seed、训练曲线或资源日志才能缩小原因范围"],
            confidence=0.24,
            verification_plan=f"为每组补充至少 3 个 seed，并记录 {mapping.primary_metric}、训练曲线与资源使用。",
        ))
    return hypotheses


def generate_proposals(hypotheses: list[Hypothesis], mapping: SchemaMapping) -> list[ExperimentProposal]:
    proposals = []
    for index, hypothesis in enumerate(hypotheses[:3], start=1):
        changed = {
            "hyp_memory_pressure": "batch_size",
            "hyp_seed_sensitivity": "seed",
            "hyp_dataset_mismatch": "dataset_version",
            "hyp_numerical_instability": "gradient_clipping",
        }.get(hypothesis.id, "seed_count")
        proposals.append(ExperimentProposal(
            id=f"proposal_{index}",
            title=f"验证：{hypothesis.description.rstrip('。')}",
            hypothesis_id=hypothesis.id,
            changed_variable=changed,
            fixed_conditions=["模型代码版本", "数据划分", "评估协议", f"主指标 {mapping.primary_metric}"],
            seeds=[17, 29, 43],
            expected_observation=hypothesis.verification_plan,
            interpretation="若异常消失或组间差异显著收窄，则支持该假设；若结果保持不变，则优先转向其他解释。",
            priority="P1" if hypothesis.confidence >= 0.7 else "P2",
            estimated_cost="3 次运行",
        ))
    return proposals


def answer_question(question: str, result: dict[str, Any]) -> dict[str, Any]:
    lowered = question.lower()
    summary = result["summary"]
    refs: list[dict[str, Any]] = []
    if any(word in lowered for word in ("方差", "波动", "seed", "稳定")):
        groups = summary["groups"]
        ranked = sorted((item for item in groups if item["std"] is not None), key=lambda item: item["std"], reverse=True)
        if ranked:
            top = ranked[0]
            refs = [{"kind": "run", "id": run_id, "label": run_id} for run_id in top["run_ids"]]
            text = f"{top['group']} 的 seed 波动最大，标准差为 {top['std']:.4g}。建议先检查该组的离群运行，再判断均值是否可信。"
        else:
            text = "当前有效运行不足，尚不能比较 seed 稳定性。"
    elif any(word in lowered for word in ("为什么", "原因", "异常", "排错")):
        hypotheses = result.get("hypotheses", [])
        if hypotheses:
            item = max(hypotheses, key=lambda row: row["confidence"])
            refs = item["supporting_evidence"]
            text = f"当前优先假设是：{item['description']} 置信度 {item['confidence']:.0%}。仍需注意：{'；'.join(item['uncertainties'])}"
        else:
            text = "当前没有足够证据形成排错假设。"
    elif any(word in lowered for word in ("三次", "3次", "怎么安排", "下一步")):
        proposal = result.get("proposals", [{}])[0]
        text = f"建议将 3 次运行用于同一最小验证：改变 {proposal.get('changed_variable', '一个变量')}，使用 seed {proposal.get('seeds', [17, 29, 43])}，其余条件全部固定。"
        hypothesis = next((item for item in result.get("hypotheses", []) if item["id"] == proposal.get("hypothesis_id")), None)
        refs = hypothesis["supporting_evidence"] if hypothesis else []
    elif any(word in lowered for word in ("baseline", "提升", "更好", "采用")):
        comparisons = summary["comparison"]
        if comparisons:
            best = max(comparisons, key=lambda item: item["mean_delta"] if summary["metric_direction"] == "maximize" else -item["mean_delta"])
            refs = [{"kind": "run", "id": ref.split(":", 1)[1], "label": ref.split(":", 1)[1]} for ref in best["evidence_refs"][:8]]
            caution = "样本量偏小，" if best["warnings"] else ""
            text = f"{best['group']} 相对 {best['baseline_group']} 的均值变化为 {best['mean_delta']:+.4g}，效应量 {best['effect_size']:.2f}。{caution}建议结合置信区间和稳定性后再决定是否采用。"
        else:
            text = "当前没有可用的 baseline 对比，请先确认 baseline 和主指标。"
    else:
        text = summary["conclusion"] + " 你可以继续追问具体运行、seed 波动、异常原因或下一轮实验安排。"
    return {"answer": text, "evidence_refs": refs, "basis": "deterministic_analysis"}


def _collect_evidence(findings: list[Finding]) -> list[EvidenceRef]:
    seen = set()
    result = []
    for finding in findings:
        for ref in finding.evidence_refs:
            key = (ref.kind, ref.id)
            if key not in seen:
                seen.add(key)
                result.append(ref)
    return result[:10]


def _safe_mean(series: Any) -> float | None:
    if series is None:
        return None
    values = pd.to_numeric(series, errors="coerce").dropna()
    return float(values.mean()) if not values.empty else None


def _conclusion(comparisons: list[dict[str, Any]], mapping: SchemaMapping) -> str:
    if not comparisons:
        return "当前数据不足以完成 baseline 对比。"
    ranked = sorted(comparisons, key=lambda item: item["mean_delta"], reverse=mapping.metric_direction == "maximize")
    best = ranked[0]
    lower, upper = best["confidence_interval"]
    favorable = best["mean_delta"] > 0 if mapping.metric_direction == "maximize" else best["mean_delta"] < 0
    crosses_zero = lower <= 0 <= upper
    if favorable and not crosses_zero:
        return f"{best['group']} 相对 {mapping.baseline_group} 的提升方向一致，置信区间未跨过 0；仍需结合样本量与异常项判断可复现性。"
    if favorable:
        return f"{best['group']} 的均值优于 {mapping.baseline_group}，但置信区间跨过 0，当前证据不足以确认稳定提升。"
    return f"当前候选组没有表现出相对 {mapping.baseline_group} 的稳定优势。"
