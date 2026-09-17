import unittest
from pathlib import Path


DOCUMENT = Path(__file__).parents[1] / "docs" / "mvp-product-design.md"
PROJECT_DESIGN = Path(__file__).parents[1] / "docs" / "experimentlens-project-design.md"


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


class ProjectDesignDocumentTest(unittest.TestCase):
    def test_project_design_contains_required_sections(self):
        content = PROJECT_DESIGN.read_text(encoding="utf-8")
        required_sections = [
            "## 4. 总体架构",
            "## 5. 技术栈",
            "## 6. 核心领域模型",
            "## 8. Microsoft Data Formulator 的具体复用方案",
            "## 9. karpathy/autoresearch 的辅助设计复用",
            "## 10. MLflow 的未来接入方案",
            "## 13. 项目搭建顺序",
            "## 14. 测试策略",
        ]

        for section in required_sections:
            with self.subTest(section=section):
                self.assertIn(section, content)

    def test_project_design_references_each_source_project(self):
        content = PROJECT_DESIGN.read_text(encoding="utf-8")
        repositories = [
            "https://github.com/microsoft/data-formulator",
            "https://github.com/karpathy/autoresearch",
            "https://github.com/mlflow/mlflow",
        ]

        for repository in repositories:
            with self.subTest(repository=repository):
                self.assertIn(repository, content)

    def test_project_design_has_no_unresolved_placeholders(self):
        content = PROJECT_DESIGN.read_text(encoding="utf-8")

        for placeholder in ("TODO", "TBD", "待补充"):
            with self.subTest(placeholder=placeholder):
                self.assertNotIn(placeholder, content)


if __name__ == "__main__":
    unittest.main()
