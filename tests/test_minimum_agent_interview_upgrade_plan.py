from pathlib import Path

ROOT = Path(__file__).parents[1]
PLAN = ROOT / "docs" / "minimum-agent-interview-upgrade-plan.md"
README = ROOT / "README.md"


def test_minimum_plan_limits_scope_to_high_value_agent_work():
    content = PLAN.read_text(encoding="utf-8")

    assert "预计工期：10～14 个工作日" in content
    assert "真实 Evaluation Harness" in content
    assert "独立可恢复 Agent Worker" in content
    assert "面试级可靠性证据和演示" in content
    assert "明确不做的功能" in content


def test_minimum_plan_defines_measurable_acceptance_criteria():
    content = PLAN.read_text(encoding="utf-8")

    required_phrases = (
        "trajectory 全部来自真实 AgentRun",
        "30 条 Evaluation",
        "三个崩溃点恢复测试全部通过",
        "100 个 AgentRun",
        "没有重复 ToolCall 和丢失事件",
        "所有性能数字都能通过仓库脚本重新生成",
    )
    for phrase in required_phrases:
        assert phrase in content


def test_minimum_plan_explicitly_defers_nonessential_infrastructure():
    content = PLAN.read_text(encoding="utf-8")

    for deferred in ("Temporal", "Redis", "Kafka", "Kubernetes", "多 Agent"):
        assert deferred in content


def test_readme_links_to_minimum_interview_plan():
    readme = README.read_text(encoding="utf-8")

    assert "docs/minimum-agent-interview-upgrade-plan.md" in readme
