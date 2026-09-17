from pathlib import Path

GUIDE = Path(__file__).parents[1] / "docs" / "user-guide.md"


def test_user_guide_covers_complete_user_journey():
    content = GUIDE.read_text(encoding="utf-8")
    required_sections = [
        "## 2. 开始使用",
        "## 3. 用户需要准备什么文件",
        "## 4. 在 ExperimentLens 中进行一次完整分析",
        "## 5. 如何阅读分析结果",
        "## 6. 如何向 Agent 追问",
        "## 7. 生成、编辑与下载报告",
        "## 9. 常见问题与故障处理",
        "## 10. 数据保存与隐私",
        "## 11. 当前 MVP 的能力边界",
        "## 12. 一页式检查清单",
    ]

    for section in required_sections:
        assert section in content


def test_user_guide_documents_supported_inputs_and_required_fields():
    content = GUIDE.read_text(encoding="utf-8")

    for extension in ("`.csv`", "`.tsv`", "`.xlsx`", "`.json`", "`.jsonl`", "`.yaml`", "`.txt`", "`.log`"):
        assert extension in content

    for field in ("`run_id`", "`group`", "`seed`", "`status`", "`duration_seconds`"):
        assert field in content


def test_user_guide_examples_and_ui_labels_match_the_product():
    content = GUIDE.read_text(encoding="utf-8")

    for label in ("新建分析", "识别实验结构", "确认并开始分析", "追问 Agent", "下载当前报告"):
        assert f"“{label}”" in content

    assert "```csv" in content
    assert "```json" in content
    assert "```yaml" in content


def test_user_guide_has_no_unresolved_placeholders():
    content = GUIDE.read_text(encoding="utf-8")

    for placeholder in ("TODO", "TBD", "待补充"):
        assert placeholder not in content
