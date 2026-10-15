from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).parents[1]
SOURCE = ROOT / "docs" / "hr-interview-question-guide.md"
DOCUMENT = ROOT / "docs" / "ExperimentLens-互联网大厂HR面试问答手册.docx"
BUILDER = ROOT / "scripts" / "build_hr_interview_word.py"


def test_hr_interview_source_covers_core_question_categories():
    content = SOURCE.read_text(encoding="utf-8")

    for marker in (
        "项目事实与 HR 表达转换",
        "个人贡献与主人翁意识问题",
        "技术难点与解决过程问题",
        "协作 沟通与冲突问题",
        "失败 压力与复盘问题",
        "岗位动机与职业规划问题",
        "压力追问与高风险问题",
        "模拟面试评分表",
        "面试前核验清单",
    ):
        assert marker in content

    assert content.count("### ") >= 65
    assert "本地 SQLite" in content
    assert "确定性离线模型" in content
    assert "不代表互联网生产 SLO" in content


def test_hr_interview_word_is_valid_and_contains_required_content():
    assert DOCUMENT.exists()
    assert DOCUMENT.stat().st_size > 50_000

    with ZipFile(DOCUMENT) as archive:
        names = set(archive.namelist())
        assert {
            "[Content_Types].xml",
            "word/document.xml",
            "word/styles.xml",
            "word/footer1.xml",
        } <= names
        document_xml = archive.read("word/document.xml").decode("utf-8")

    for marker in (
        "ExperimentLens 互联网大厂 HR 面试问答手册",
        "请用三十秒介绍这个项目",
        "你在项目中的角色是什么",
        "项目最难的地方是什么",
        "为什么投递我们公司",
        "这是不是一个套壳项目",
        "适合向 HR 反问的问题",
        "30 条",
        "100 个",
        "EvidenceRef",
        "fencing token",
    ):
        assert marker in document_xml

    assert document_xml.count("<w:tbl>") >= 3
    assert document_xml.count("<w:hyperlink") >= 20


def test_hr_interview_word_builder_and_readme_link_are_present():
    builder = BUILDER.read_text(encoding="utf-8")
    assert "build_document" in builder
    assert "ExperimentLens-互联网大厂HR面试问答手册.docx" in builder

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "docs/ExperimentLens-互联网大厂HR面试问答手册.docx" in readme
