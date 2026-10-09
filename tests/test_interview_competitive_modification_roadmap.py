from pathlib import Path

ROOT = Path(__file__).parents[1]
ROADMAP = ROOT / "docs" / "interview-competitive-modification-roadmap.md"
README = ROOT / "README.md"


def test_roadmap_distinguishes_current_state_from_planned_work():
    content = ROADMAP.read_text(encoding="utf-8")

    assert "## 3. 当前版本实际情况" in content
    assert "### 3.1 已实现能力" in content
    assert "### 3.2 部分实现能力" in content
    assert "### 3.3 尚未实现的关键能力" in content
    assert "还不能宣称是生产级分布式 Agent 平台" in content


def test_roadmap_covers_the_required_delivery_stages_and_evidence():
    content = ROADMAP.read_text(encoding="utf-8")

    required_phrases = (
        "阶段 P1：真实 Evaluation Harness",
        "阶段 P2：控制面与执行面分离",
        "阶段 P3：Outbox 与实时事件闭环",
        "阶段 P4：真实 MLflow 数据源与曲线诊断",
        "阶段 P5：Proposal 审批与结果回流",
        "阶段 P6：身份、权限与审计",
        "阶段 P7：性能、可靠性与交付证明",
        "故障测试",
        "统一完成定义",
        "面试交付物",
    )

    for phrase in required_phrases:
        assert phrase in content


def test_readme_links_to_interview_competitive_roadmap():
    readme = README.read_text(encoding="utf-8")

    assert "docs/interview-competitive-modification-roadmap.md" in readme
