from pathlib import Path

PLAN = Path(__file__).parents[1] / "docs" / "experimentlens-2.0-expansion-plan.md"


def test_2_0_plan_covers_interview_grade_architecture_and_delivery():
    content = PLAN.read_text(encoding="utf-8")

    for section in (
        "目标架构",
        "服务化与持久化工作流",
        "模型网关与确定性工具平台",
        "Trace、日志、指标与成本可观测性",
        "Agent 评测与质量门禁",
        "多租户、安全和供应链",
        "性能、可靠性与混沌测试",
        "部署、CI/CD 与本地可复现环境",
        "面试展示方案",
    ):
        assert section in content


def test_2_0_plan_names_required_engineering_tools_and_patterns():
    content = PLAN.read_text(encoding="utf-8")

    for term in (
        "PostgreSQL",
        "Temporal",
        "Transactional Outbox",
        "Redis Streams",
        "OpenTelemetry",
        "Prometheus",
        "MLflow",
        "Locust",
        "CodeQL",
        "Kubernetes",
        "Golden Dataset",
        "EvidenceRef",
    ):
        assert term in content


def test_2_0_plan_keeps_claims_measurable_and_safe():
    content = PLAN.read_text(encoding="utf-8")

    assert "这些数字是目标，不得直接写进简历" in content
    assert "跨项目读取成功数为 0" in content
    assert "无效 EvidenceRef 数量为 0" in content
    assert "禁止任意 Shell" in content
    assert "Decision Rule" in content
    assert "每次提交保持可运行" in content
