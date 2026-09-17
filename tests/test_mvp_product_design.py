import unittest
from pathlib import Path


DOCUMENT = Path(__file__).parents[1] / "docs" / "mvp-product-design.md"


class MvpProductDesignDocumentTest(unittest.TestCase):
    def test_document_contains_required_sections(self):
        content = DOCUMENT.read_text(encoding="utf-8")
        required_sections = [
            "## 1. 产品概述",
            "## 2. 目标用户",
            "## 3. MVP 目标",
            "## 4. 主要功能",
            "## 5. 核心交互流程",
            "## 6. MVP 范围边界",
            "## 8. 成功指标",
        ]

        for section in required_sections:
            with self.subTest(section=section):
                self.assertIn(section, content)

    def test_document_has_no_unresolved_placeholders(self):
        content = DOCUMENT.read_text(encoding="utf-8")

        for placeholder in ("TODO", "TBD", "待补充"):
            with self.subTest(placeholder=placeholder):
                self.assertNotIn(placeholder, content)


if __name__ == "__main__":
    unittest.main()
