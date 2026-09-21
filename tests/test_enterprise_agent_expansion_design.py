from pathlib import Path

DOCUMENT = Path(__file__).parents[1] / "docs" / "enterprise-agent-expansion-design.md"


def test_expansion_design_covers_product_engineering_and_delivery():
    content = DOCUMENT.read_text(encoding="utf-8")
    required_sections = [
        "## 2. 调研依据与结论边界",
        "## 3. 当前 MVP 的能力盘点",
        "## 4. 下一阶段产品定位",
        "## 6. 总体技术架构",
        "## 7. 功能扩充设计",
        "## 10. 评测、测试与质量门禁",
        "## 11. 分阶段实施计划",
        "## 12. 面试演示方案",
        "## 13. 项目完成定义",
    ]

    for section in required_sections:
        assert section in content


def test_expansion_design_prioritizes_production_agent_capabilities():
    content = DOCUMENT.read_text(encoding="utf-8")
    capabilities = [
        "Agent Runtime",
        "Agent 全链路可观测",
        "Agent 评测与回归门禁",
        "通用实验源接口与 MLflow 增量连接器",
        "实验过程曲线和资源异常分析",
        "安全、权限与审计",
        "服务化、异步任务和部署",
    ]

    for capability in capabilities:
        assert capability in content


def test_expansion_design_references_official_company_sources():
    content = DOCUMENT.read_text(encoding="utf-8")
    official_domains = [
        "careers.tencent.com",
        "cloud.tencent.com",
        "jobs.bytedance.com",
        "volcengine.com",
        "career.huawei.com",
        "support.huaweicloud.com",
    ]

    for domain in official_domains:
        assert domain in content


def test_expansion_design_is_not_limited_to_machine_learning_teams():
    content = DOCUMENT.read_text(encoding="utf-8")
    supported_experiments = [
        "传统机器学习",
        "深度学习训练",
        "强化学习",
        "推荐与搜索",
        "大模型与 Agent",
        "推理与系统性能",
        "其他计算机与 AI 实验",
    ]

    assert "面向机器学习团队的 ExperimentOps" not in content
    assert "不要求一定包含模型训练" in content
    assert "ExperimentSource" in content
    for experiment_type in supported_experiments:
        assert experiment_type in content


def test_expansion_design_has_measurable_acceptance_criteria_and_no_placeholders():
    content = DOCUMENT.read_text(encoding="utf-8")

    assert "EvidenceRef 有效率保持 100%" in content
    assert "10,000 个 runs" in content
    assert "总周期约 9 周" in content
    for placeholder in ("TODO", "TBD", "待补充"):
        assert placeholder not in content
