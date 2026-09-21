from pathlib import Path

DOCUMENT = Path(__file__).parents[1] / "docs" / "project-modification-plan.md"


def test_modification_plan_covers_every_implementation_layer():
    content = DOCUMENT.read_text(encoding="utf-8")
    required_sections = [
        "## 3. 当前代码与目标变化",
        "## 4. 目标代码结构",
        "## 6. 阶段 1：通用实验模型与多指标分析",
        "## 7. 阶段 2：实现真正的 Agent Runtime",
        "## 8. 阶段 3：Trace、评测与安全门禁",
        "## 9. 阶段 4：实验连接器与过程诊断",
        "## 10. 阶段 5：下一轮实验回流闭环",
        "## 11. 阶段 6：服务化与交付",
        "## 12. 前端页面修改总表",
        "## 13. 数据迁移方案",
        "## 14. 测试修改方案",
    ]

    for section in required_sections:
        assert section in content


def test_modification_plan_is_grounded_in_the_current_repository():
    content = DOCUMENT.read_text(encoding="utf-8")
    current_files = [
        "py-src/experimentlens/app.py",
        "domain.py",
        "ingestion.py",
        "analysis.py",
        "service.py",
        "workspace.py",
        "src/App.tsx",
        "src/api.ts",
        "src/store.ts",
    ]

    for filename in current_files:
        assert filename in content


def test_modification_plan_preserves_general_experiment_scope():
    content = DOCUMENT.read_text(encoding="utf-8")
    required_concepts = [
        "机器学习、深度学习",
        "强化学习",
        "Agent 评测",
        "系统 Benchmark",
        "ExperimentSource",
        "MetricDefinition",
    ]

    for concept in required_concepts:
        assert concept in content


def test_modification_plan_has_migration_acceptance_and_no_placeholders():
    content = DOCUMENT.read_text(encoding="utf-8")

    assert "V1 到 V2 映射" in content
    assert "九周实施顺序" in content
    assert "修改完成定义" in content
    assert "至少 50 个 Agent Eval 案例" in content
    for placeholder in ("TODO", "TBD", "待补充"):
        assert placeholder not in content
