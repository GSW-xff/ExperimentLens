from __future__ import annotations

from pathlib import Path

from ..domain import Project
from ..repositories.interfaces import ExperimentRepository
from .analysis import AnalysisService


class ReportService:
    def __init__(self, repository: ExperimentRepository, analysis: AnalysisService) -> None:
        self.repository = repository
        self.analysis = analysis

    def generate_report(self, project_id: str) -> dict[str, str]:
        project = self.repository.get_project(project_id)
        markdown = render_report(project, self.analysis.get_analysis(project_id))
        path = self.repository.project_dir(project_id) / "reports" / "analysis-report.md"
        path.write_text(markdown, encoding="utf-8")
        return {"markdown": markdown, "filename": path.name}

    def save_report_html(self, project_id: str, html: str) -> Path:
        if not html.strip():
            raise ValueError("报告内容不能为空")
        if len(html.encode("utf-8")) > 5 * 1024 * 1024:
            raise ValueError("报告内容过大")
        path = self.repository.project_dir(project_id) / "reports" / "analysis-report.html"
        document = (
            '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            "<title>ExperimentLens 分析报告</title></head><body>"
            f"{html}</body></html>"
        )
        path.write_text(document, encoding="utf-8")
        return path


def render_report(project: Project, result: dict) -> str:
    summary = result["summary"]
    lines = [
        f"# {project.name} · 实验诊断报告", "", f"> 目标：{project.objective}", "",
        "## 结论摘要", "", summary["conclusion"], "",
        f"- 主指标：`{summary['primary_metric']}`（{'越高越好' if summary['metric_direction'] == 'maximize' else '越低越好'}）",
        f"- Baseline：`{summary['baseline_group']}`",
        f"- 数据范围：{summary['run_count']} 个 runs，{summary['group_count']} 个实验组",
        f"- 异常：{summary['findings_count']} 项，其中 {summary['high_priority_findings']} 项需优先处理",
        "", "## 组间统计", "",
        "| 实验组 | n | 均值 | 标准差 | 95% CI |", "|---|---:|---:|---:|---|",
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
            f"### {hypothesis['description']}（置信度 {hypothesis['confidence']:.0%}）", "",
            f"- 支持证据：{refs}", f"- 不确定性：{'；'.join(hypothesis['uncertainties'])}",
            f"- 验证方法：{hypothesis['verification_plan']}", "",
        ])
    lines.extend(["## 下一轮最小实验", ""])
    for proposal in result["proposals"]:
        lines.extend([
            f"### {proposal['priority']} · {proposal['title']}", "",
            f"- 唯一主要变量：`{proposal['changed_variable']}`",
            f"- Seed：{', '.join(map(str, proposal['seeds']))}",
            f"- 保持不变：{'、'.join(proposal['fixed_conditions'])}",
            f"- 判断标准：{proposal['interpretation']}", "",
        ])
    sources = "、".join(source["name"] for source in project.sources) or "未记录"
    lines.extend(["## 数据与可追溯性", "", f"数据文件：{sources}", "", "分析器：ExperimentLens deterministic analysis v1.0", ""])
    return "\n".join(lines)
