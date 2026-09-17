from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

import pandas as pd

from .analysis import analyze, answer_question
from .domain import Project, SchemaMapping
from .ingestion import (
    combine_tables,
    infer_mapping,
    infer_run_from_text,
    normalize,
    parse_file,
)
from .workspace import Workspace


class ExperimentService:
    def __init__(self, workspace: Workspace):
        self.workspace = workspace

    def create_project(self, name: str, objective: str) -> Project:
        if not name.strip():
            raise ValueError("项目名称不能为空")
        return self.workspace.create_project(name, objective)

    def ingest_paths(self, project_id: str, paths: list[Path]) -> dict[str, Any]:
        project = self.workspace.get_project(project_id)
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
            self.workspace.write_json(project_id, "scratch/raw_table.json", json.loads(frame.to_json(orient="records", force_ascii=False)))
        existing_configs = self.workspace.read_json(project_id, "scratch/configs.json", [])
        existing_logs = self.workspace.read_json(project_id, "scratch/logs.json", [])
        self.workspace.write_json(project_id, "scratch/configs.json", [*existing_configs, *configs])
        self.workspace.write_json(project_id, "scratch/logs.json", [*existing_logs, *logs])
        project.sources.extend(source_summaries)
        project.state = "mapping" if not frame.empty else "awaiting_results"
        self.workspace.save_project(project)
        suggestion = None
        confidence = None
        preview: list[dict[str, Any]] = []
        if not frame.empty:
            mapping, confidence = infer_mapping(frame)
            project.mapping = mapping
            self.workspace.save_project(project)
            suggestion = mapping.model_dump()
            preview = _clean_records(frame.head(12))
        return {"sources": source_summaries, "mapping": suggestion, "confidence": confidence, "preview": preview}

    def confirm_mapping(self, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        project = self.workspace.get_project(project_id)
        mapping = SchemaMapping.model_validate(payload)
        records = self.workspace.read_json(project_id, "scratch/raw_table.json", [])
        if not records:
            raise ValueError("请先上传实验结果表")
        frame = pd.DataFrame(records)
        runs, metrics, params = normalize(frame, mapping)
        configs = self.workspace.read_json(project_id, "scratch/configs.json", [])
        params = _merge_configs(params, runs, configs)
        logs = self.workspace.read_json(project_id, "scratch/logs.json", [])
        known_run_ids = set(runs["run_id"].astype(str))
        for record in logs:
            record["run_id"] = infer_run_from_text(f"{record.get('source', '')} {record.get('text', '')}", known_run_ids)
        self.workspace.write_frame(project_id, "runs", runs)
        self.workspace.write_frame(project_id, "metrics", metrics)
        self.workspace.write_frame(project_id, "params", params)
        self.workspace.write_json(project_id, "normalized/artifacts.json", logs)
        project.mapping = mapping
        project.state = "ready"
        self.workspace.save_project(project)
        return {"run_count": len(runs), "metric_count": len(metrics), "parameter_count": len(params), "mapping": mapping.model_dump()}

    def run_analysis(self, project_id: str) -> dict[str, Any]:
        project = self.workspace.get_project(project_id)
        if not project.mapping:
            raise ValueError("请先确认字段映射")
        result = analyze(
            self.workspace.read_frame(project_id, "runs"),
            self.workspace.read_frame(project_id, "metrics"),
            self.workspace.read_frame(project_id, "params"),
            self.workspace.read_json(project_id, "normalized/artifacts.json", []),
            project.mapping,
        )
        for name in ("summary", "findings", "hypotheses", "proposals"):
            self.workspace.write_json(project_id, f"analysis/{name}.json", result[name])
        project.state = "analyzed"
        self.workspace.save_project(project)
        return result

    def get_analysis(self, project_id: str) -> dict[str, Any]:
        summary = self.workspace.read_json(project_id, "analysis/summary.json")
        if summary is None:
            return self.run_analysis(project_id)
        return {
            "summary": summary,
            "findings": self.workspace.read_json(project_id, "analysis/findings.json", []),
            "hypotheses": self.workspace.read_json(project_id, "analysis/hypotheses.json", []),
            "proposals": self.workspace.read_json(project_id, "analysis/proposals.json", []),
        }

    def get_runs(self, project_id: str) -> list[dict[str, Any]]:
        project = self.workspace.get_project(project_id)
        runs = self.workspace.read_frame(project_id, "runs")
        metrics = self.workspace.read_frame(project_id, "metrics")
        params = self.workspace.read_frame(project_id, "params")
        if runs.empty:
            return []
        metric_key = project.mapping.primary_metric if project.mapping else None
        primary = metrics[metrics["key"] == metric_key][["run_id", "value"]] if metric_key and not metrics.empty else pd.DataFrame(columns=["run_id", "value"])
        wide = runs.merge(primary.rename(columns={"value": "metric_value"}), on="run_id", how="left")
        params_by_run: dict[str, dict[str, str]] = {}
        for row in params.itertuples():
            params_by_run.setdefault(str(row.run_id), {})[str(row.key)] = str(row.value)
        result = []
        for row in wide.to_dict(orient="records"):
            cleaned = {key: (None if pd.isna(value) else value) for key, value in row.items()}
            cleaned["params"] = params_by_run.get(str(cleaned["run_id"]), {})
            result.append(cleaned)
        return result

    def chat(self, project_id: str, question: str) -> dict[str, Any]:
        if not question.strip():
            raise ValueError("问题不能为空")
        return answer_question(question, self.get_analysis(project_id))

    def generate_report(self, project_id: str) -> dict[str, str]:
        project = self.workspace.get_project(project_id)
        result = self.get_analysis(project_id)
        markdown = render_report(project, result)
        path = self.workspace.project_dir(project_id) / "reports" / "analysis-report.md"
        path.write_text(markdown, encoding="utf-8")
        return {"markdown": markdown, "filename": path.name}

    def save_report_html(self, project_id: str, html: str) -> Path:
        if not html.strip():
            raise ValueError("报告内容不能为空")
        if len(html.encode("utf-8")) > 5 * 1024 * 1024:
            raise ValueError("报告内容过大")
        path = self.workspace.project_dir(project_id) / "reports" / "analysis-report.html"
        document = (
            "<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            "<title>ExperimentLens 分析报告</title></head><body>"
            f"{html}</body></html>"
        )
        path.write_text(document, encoding="utf-8")
        return path

    def create_demo(self) -> Project:
        project = self.create_project("Transformer 调参实验", "在不显著增加训练成本的前提下，提高验证集准确率并保持多 seed 稳定性。")
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
        self.workspace.write_json(project.id, "scratch/raw_table.json", json.loads(frame.to_json(orient="records")))
        logs = [
            {"source": "large-29.log", "line": 148, "text": "RuntimeError: CUDA out of memory. Tried to allocate 1.50 GiB", "run_id": "large-29"},
            {"source": "large-43.log", "line": 102, "text": "warning: validation accuracy oscillation detected", "run_id": "large-43"},
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


def _merge_configs(params: pd.DataFrame, runs: pd.DataFrame, configs: list[dict[str, Any]]) -> pd.DataFrame:
    records = params.to_dict(orient="records") if not params.empty else []
    known = set(runs["run_id"].astype(str))
    for config in configs:
        run_id = next((str(config[key]) for key in ("run_id", "run", "trial_id") if key in config), None)
        if run_id not in known:
            continue
        for key, value in _flatten(config).items():
            if key not in {"run_id", "run", "trial_id", "source"}:
                records.append({"run_id": run_id, "key": key, "value": str(value), "value_type": type(value).__name__})
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


def render_report(project: Project, result: dict[str, Any]) -> str:
    summary = result["summary"]
    lines = [
        f"# {project.name} · 实验诊断报告",
        "",
        f"> 目标：{project.objective}",
        "",
        "## 结论摘要",
        "",
        summary["conclusion"],
        "",
        f"- 主指标：`{summary['primary_metric']}`（{'越高越好' if summary['metric_direction'] == 'maximize' else '越低越好'}）",
        f"- Baseline：`{summary['baseline_group']}`",
        f"- 数据范围：{summary['run_count']} 个 runs，{summary['group_count']} 个实验组",
        f"- 异常：{summary['findings_count']} 项，其中 {summary['high_priority_findings']} 项需优先处理",
        "",
        "## 组间统计",
        "",
        "| 实验组 | n | 均值 | 标准差 | 95% CI |",
        "|---|---:|---:|---:|---|",
    ]
    for group in summary["groups"]:
        if group["mean"] is None:
            lines.append(f"| {group['group']} | 0 | — | — | — |")
        else:
            lines.append(f"| {group['group']} | {group['n']} | {group['mean']:.4f} | {group['std']:.4f} | [{group['ci_low']:.4f}, {group['ci_high']:.4f}] |")
    lines.extend(["", "## 异常与证据", ""])
    for finding in result["findings"]:
        refs = "、".join(ref["label"] for ref in finding["evidence_refs"])
        lines.extend([f"### {finding['title']}", "", finding["description"], "", f"证据：{refs}", ""])
    lines.extend(["## 排错假设", ""])
    for hypothesis in result["hypotheses"]:
        refs = "、".join(ref["label"] for ref in hypothesis["supporting_evidence"]) or "暂无直接证据"
        lines.extend([
            f"### {hypothesis['description']}（置信度 {hypothesis['confidence']:.0%}）",
            "",
            f"- 支持证据：{refs}",
            f"- 不确定性：{'；'.join(hypothesis['uncertainties'])}",
            f"- 验证方法：{hypothesis['verification_plan']}",
            "",
        ])
    lines.extend(["## 下一轮最小实验", ""])
    for proposal in result["proposals"]:
        lines.extend([
            f"### {proposal['priority']} · {proposal['title']}",
            "",
            f"- 唯一主要变量：`{proposal['changed_variable']}`",
            f"- Seed：{', '.join(map(str, proposal['seeds']))}",
            f"- 保持不变：{'、'.join(proposal['fixed_conditions'])}",
            f"- 判断标准：{proposal['interpretation']}",
            "",
        ])
    sources = "、".join(source["name"] for source in project.sources) or "未记录"
    lines.extend(["## 数据与可追溯性", "", f"数据文件：{sources}", "", "分析器：ExperimentLens deterministic analysis v1.0", ""])
    return "\n".join(lines)
