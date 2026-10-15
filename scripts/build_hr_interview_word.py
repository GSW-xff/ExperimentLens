from __future__ import annotations

import argparse
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import build_onboarding_word as common
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

TITLE = "ExperimentLens 互联网大厂 HR 面试问答手册"
SUBTITLE = "项目表达  高频问题  参考回答  真实性边界"

# The bundled LibreOffice renderer includes Noto CJK fonts.  Using the macOS-only
# Hiragino family here would make Chinese text disappear in headless QA renders.
common.BODY_FONT = "Heiti SC"
common.LATIN_FONT = "Heiti SC"

WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def register_document_font(document_path: Path, font_name: str) -> None:
    """Declare the selected CJK font in fontTable.xml for LibreOffice compatibility."""
    ET.register_namespace("w", WORD_NS)
    ET.register_namespace("r", REL_NS)

    with ZipFile(document_path) as archive:
        entries = {name: archive.read(name) for name in archive.namelist()}

    font_table = ET.fromstring(entries["word/fontTable.xml"])
    font_element = next(
        (
            node
            for node in font_table.findall(f"{{{WORD_NS}}}font")
            if node.get(f"{{{WORD_NS}}}name") == font_name
        ),
        None,
    )
    if font_element is None:
        font_element = ET.SubElement(
            font_table, f"{{{WORD_NS}}}font", {f"{{{WORD_NS}}}name": font_name}
        )
        ET.SubElement(
            font_element, f"{{{WORD_NS}}}charset", {f"{{{WORD_NS}}}val": "86"}
        )
        ET.SubElement(
            font_element, f"{{{WORD_NS}}}family", {f"{{{WORD_NS}}}val": "swiss"}
        )
        ET.SubElement(
            font_element, f"{{{WORD_NS}}}pitch", {f"{{{WORD_NS}}}val": "variable"}
        )

    entries["word/fontTable.xml"] = ET.tostring(
        font_table, encoding="utf-8", xml_declaration=True
    )

    temporary = document_path.with_suffix(".embedded.docx")
    with ZipFile(temporary, "w", ZIP_DEFLATED) as archive:
        for name, payload in entries.items():
            archive.writestr(name, payload)
    temporary.replace(document_path)


def add_footer(document: Document) -> None:
    footer = document.sections[0].footer
    paragraph = footer.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    label = paragraph.add_run("ExperimentLens HR 面试手册    ")
    common.set_run_font(label, common.BODY_FONT, 8.5)
    label.font.color.rgb = RGBColor(89, 89, 89)
    field = OxmlElement("w:fldSimple")
    field.set(qn("w:instr"), "PAGE")
    field_run = OxmlElement("w:r")
    properties = OxmlElement("w:rPr")
    fonts = OxmlElement("w:rFonts")
    fonts.set(qn("w:ascii"), common.LATIN_FONT)
    fonts.set(qn("w:hAnsi"), common.LATIN_FONT)
    fonts.set(qn("w:eastAsia"), common.BODY_FONT)
    size = OxmlElement("w:sz")
    size.set(qn("w:val"), "17")
    color = OxmlElement("w:color")
    color.set(qn("w:val"), "595959")
    properties.extend([fonts, size, color])
    field_run.append(properties)
    value = OxmlElement("w:t")
    value.text = "1"
    field_run.append(value)
    field.append(field_run)
    paragraph._p.append(field)


def add_code_block(document: Document, lines: list[str]) -> None:
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.left_indent = Inches(0.18)
    paragraph.paragraph_format.right_indent = Inches(0.12)
    paragraph.paragraph_format.space_before = Pt(5)
    paragraph.paragraph_format.space_after = Pt(7)
    paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
    properties = paragraph._p.get_or_add_pPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), common.CODE_BG)
    properties.append(shading)
    for index, line in enumerate(lines or [""]):
        run = paragraph.add_run(line)
        common.set_run_font(run, common.CODE_FONT, 8.7)
        if index < len(lines) - 1:
            run.add_break(WD_BREAK.LINE)


def build_document(source_path: Path, output_path: Path) -> None:
    source = source_path.read_text(encoding="utf-8")
    sections, lines = common.parse_source(source)
    document = Document()
    common.configure_styles(document)
    document.core_properties.title = TITLE
    document.core_properties.subject = "互联网大厂 HR 面试中的 ExperimentLens 项目表达与问答准备"
    document.core_properties.author = "ExperimentLens Project"
    document.core_properties.keywords = "ExperimentLens, HR 面试, AI Agent, 项目问答"

    section = document.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(0.72)
    section.bottom_margin = Inches(0.68)
    section.left_margin = Inches(0.8)
    section.right_margin = Inches(0.8)
    section.header_distance = Inches(0.28)
    section.footer_distance = Inches(0.3)
    add_footer(document)

    spacer = document.add_paragraph()
    spacer.paragraph_format.space_after = Pt(72)
    title = document.add_paragraph(TITLE, style="Title")
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle = document.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle_run = subtitle.add_run(SUBTITLE)
    common.set_run_font(subtitle_run, common.BODY_FONT, 14, bold=True)
    subtitle.paragraph_format.space_after = Pt(30)
    audience = document.add_paragraph()
    audience.alignment = WD_ALIGN_PARAGRAPH.CENTER
    audience_run = audience.add_run("适用于 AI Agent  后端  平台工程  机器学习工程与研发实习岗位")
    common.set_run_font(audience_run, common.BODY_FONT, 10.8)
    audience.paragraph_format.space_after = Pt(12)
    boundary = document.add_paragraph()
    boundary.alignment = WD_ALIGN_PARAGRAPH.CENTER
    boundary_run = boundary.add_run("回答必须与真实经历一致  项目能力不等于个人独立贡献")
    common.set_run_font(boundary_run, common.BODY_FONT, 10)
    boundary_run.italic = True
    boundary_run.font.color.rgb = RGBColor(89, 89, 89)
    document.add_page_break()

    intro = document.add_paragraph("使用说明", style="Heading 1")
    intro.paragraph_format.page_break_before = False
    common.add_body_paragraph(
        document,
        "本手册将 ExperimentLens 的技术事实转换为 HR 面试可以理解的项目价值、个人贡献、难点、结果、协作和职业动机。建议先确定真实贡献口径，再选择与目标岗位相关的问题练习。",
    )
    common.add_body_paragraph(
        document,
        "示范答案可以帮助组织语言，但不能直接代替个人经历。所有涉及设计、实现、主导、数据和团队协作的表述，都应能通过代码、测试、文档或 commit 核验。",
    )
    common.add_body_paragraph(
        document,
        "文档中的 30 条评测与 100 任务可靠性数据来自仓库当前公开基线。它们适用于本地 SQLite 和确定性离线模型环境，不代表真实大模型或互联网生产服务等级。",
    )

    toc = document.add_paragraph("目录", style="Heading 1")
    toc.paragraph_format.page_break_before = True
    for heading, bookmark in sections:
        paragraph = document.add_paragraph(style="List Number")
        paragraph.paragraph_format.space_after = Pt(3)
        common.add_hyperlink(paragraph, heading, bookmark, internal=True)
    document.add_page_break()

    section_number = 0
    started_body = False
    in_code = False
    code_lines: list[str] = []
    table_rows: list[list[str]] = []
    quote_lines: list[str] = []

    def flush_table() -> None:
        nonlocal table_rows
        if table_rows:
            common.add_table(document, table_rows)
            table_rows = []

    def flush_quote() -> None:
        nonlocal quote_lines
        if quote_lines:
            common.add_quote(document, " ".join(line for line in quote_lines if line))
            quote_lines = []

    for raw_line in lines:
        line = raw_line.rstrip()
        if line.startswith("# ") and not started_body:
            continue
        if line.startswith("## "):
            flush_table()
            flush_quote()
            started_body = True
            section_number += 1
            heading = common.sanitize_heading(line[3:])
            paragraph = document.add_paragraph(heading, style="Heading 1")
            paragraph.paragraph_format.page_break_before = False
            common.add_bookmark(paragraph, f"section_{section_number}", section_number)
            continue
        if not started_body:
            continue
        if line.startswith("```"):
            flush_table()
            flush_quote()
            if in_code:
                add_code_block(document, code_lines)
                code_lines = []
                in_code = False
            else:
                in_code = True
            continue
        if in_code:
            code_lines.append(line)
            continue
        if line.startswith("|") and line.endswith("|"):
            flush_quote()
            table_rows.append(common.parse_table_row(line))
            continue
        flush_table()
        if line.startswith(">"):
            quote_lines.append(line[1:].strip())
            continue
        flush_quote()
        if not line.strip() or line.strip() == "---":
            continue
        if line.startswith("### "):
            document.add_paragraph(common.sanitize_heading(line[4:]), style="Heading 2")
        elif line.startswith("#### "):
            document.add_paragraph(common.sanitize_heading(line[5:]), style="Heading 3")
        elif re.match(r"^- \[[ xX]\] ", line):
            checked = line[3].lower() == "x"
            common.add_body_paragraph(document, f"{'☑' if checked else '☐'} {line[6:]}")
        elif line.startswith("- "):
            common.add_body_paragraph(document, line[2:], style="List Bullet")
        elif re.match(r"^\d+\. ", line):
            paragraph = common.add_body_paragraph(document, line)
            paragraph.paragraph_format.left_indent = Inches(0.22)
            paragraph.paragraph_format.first_line_indent = Inches(-0.22)
        else:
            common.add_body_paragraph(document, line)
    flush_table()
    flush_quote()
    if in_code:
        add_code_block(document, code_lines)

    for current_section in document.sections:
        current_section.page_width = Inches(8.5)
        current_section.page_height = Inches(11)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    document.save(output_path)
    register_document_font(output_path, common.BODY_FONT)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the ExperimentLens HR interview Word guide")
    parser.add_argument(
        "--source", default="docs/hr-interview-question-guide.md", type=Path
    )
    parser.add_argument(
        "--output", default="docs/ExperimentLens-互联网大厂HR面试问答手册.docx", type=Path
    )
    args = parser.parse_args()
    build_document(args.source, args.output)


if __name__ == "__main__":
    main()
