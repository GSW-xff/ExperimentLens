from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).parents[1]
DOCUMENT = ROOT / "docs" / "ExperimentLens-Agent-学习与面试手册.docx"
BUILDER = ROOT / "scripts" / "build_onboarding_word.py"


def test_word_handbook_is_a_valid_docx_with_required_parts():
    assert DOCUMENT.exists()
    assert DOCUMENT.stat().st_size > 100_000

    with ZipFile(DOCUMENT) as archive:
        names = set(archive.namelist())
        assert {
            "[Content_Types].xml",
            "word/document.xml",
            "word/styles.xml",
            "word/footer1.xml",
        } <= names


def test_word_handbook_contains_core_learning_and_interview_content():
    with ZipFile(DOCUMENT) as archive:
        document_xml = archive.read("word/document.xml").decode("utf-8")

    for marker in (
        "ExperimentLens 从零学习与面试讲解手册",
        "AI Agent 基础",
        "专业架构讲解",
        "技术栈总览",
        "面向 HR 的讲法",
        "技术面试高频追问与参考回答",
        "建议的新手学习与接管路线",
        "EvidenceValidator",
        "fencing token",
        "Last-Event-ID",
        "30/30",
        "100/100",
    ):
        assert marker in document_xml

    assert document_xml.count("<w:tbl>") >= 10
    assert document_xml.count("<w:hyperlink") >= 20


def test_word_handbook_builder_is_reproducible_and_readmes_link_to_output():
    source = BUILDER.read_text(encoding="utf-8")
    assert "python-docx" not in source
    assert "build_document" in source
    assert "ExperimentLens-Agent-学习与面试手册.docx" in source

    for readme in (ROOT / "README.md", ROOT / "README_EN.md"):
        assert "docs/ExperimentLens-Agent-学习与面试手册.docx" in readme.read_text(
            encoding="utf-8"
        )
