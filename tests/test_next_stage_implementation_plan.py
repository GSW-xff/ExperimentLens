from pathlib import Path

PLAN = Path(__file__).parents[1] / "docs" / "next-stage-implementation-plan.md"


def test_next_stage_plan_covers_the_complete_delivery_path():
    content = PLAN.read_text(encoding="utf-8")

    required_sections = (
        "阶段一：Schema V2 与多指标分析",
        "阶段二：真正的 Agent Runtime",
        "阶段三：SSE 实时事件流与 Agent 面板",
        "阶段四：Trace、Evaluation 与安全门禁",
        "阶段五：ExperimentSource、MLflow 与曲线诊断",
        "阶段六：Proposal 审批、回流与验证",
        "阶段七：服务化与生产交付",
        "下一批完成定义",
    )
    for section in required_sections:
        assert section in content


def test_next_stage_plan_defines_agent_and_sse_contracts():
    content = PLAN.read_text(encoding="utf-8")

    for tool in ("list_runs", "compare_groups", "search_logs", "diff_configs"):
        assert f"`{tool}`" in content
    for endpoint in (
        "POST /api/projects/:project_id/agent-runs",
        "GET  /api/agent-runs/:agent_run_id/stream",
        "POST /api/agent-runs/:agent_run_id/cancel",
    ):
        assert endpoint in content
    for event in ("tool.started", "tool.completed", "approval.required", "agent.completed"):
        assert event in content
    assert "Last-Event-ID" in content


def test_next_stage_plan_keeps_safety_and_compatibility_explicit():
    content = PLAN.read_text(encoding="utf-8")

    assert "未配置模型时规则回答继续工作" in content
    assert "无效 EvidenceRef 数量必须为 0" in content
    assert "跨项目读取成功数必须为 0" in content
    assert "Decision rule 必须在新结果产生前保存" in content
