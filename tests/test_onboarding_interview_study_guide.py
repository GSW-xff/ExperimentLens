import json
import re
from pathlib import Path

ROOT = Path(__file__).parents[1]
GUIDE = ROOT / "docs" / "onboarding-and-interview-study-guide.md"


def test_guide_covers_beginner_professional_and_interview_learning_paths():
    content = GUIDE.read_text(encoding="utf-8")

    for section in (
        "## 2. 先用最通俗的方式理解",
        "## 3. 需要先学会的实验分析基本词汇",
        "## 4. AI Agent 基础：它和普通聊天机器人有什么区别",
        "## 6. 专业架构讲解",
        "## 11. 技术栈总览：是什么、做什么、一般怎么用",
        "## 13. 面向 HR 的讲法",
        "## 14. 技术面试高频追问与参考回答",
        "## 16. 建议的新手学习与接管路线",
        "## 17. 最容易说错的地方",
        "## 19. 最终自测题",
    ):
        assert section in content


def test_guide_documents_the_real_agent_runtime_and_safety_boundaries():
    content = GUIDE.read_text(encoding="utf-8")

    for marker in (
        "list_runs",
        "compare_groups",
        "search_logs",
        "diff_configs",
        "inspect_metric_series",
        "get_finding_evidence",
        "EvidenceValidator",
        "Lease、heartbeat 和 fencing token",
        "Last-Event-ID",
        "Transactional Outbox",
        "30/30",
        "100/100",
        "本地 SQLite + 离线模型基线",
    ):
        assert marker in content

    for honest_boundary in (
        "当前是一个受约束 Orchestrator",
        "Redis 只在可选 profile",
        "Temporal 未接入",
        "MinIO 只是可选 profile",
        "当前项目没有真正的用户认证",
    ):
        assert honest_boundary in content


def test_guide_documents_commands_and_source_code_map():
    content = GUIDE.read_text(encoding="utf-8")

    for command in (
        "./scripts/start_local.sh",
        "experimentlens-api",
        "experimentlens-worker",
        "experimentlens-eval",
        "experimentlens-benchmark --runs 100 --workers 2",
        "make verify",
        "docker compose up --build",
    ):
        assert command in content

    for source in (
        "py-src/experimentlens/agent/orchestrator.py",
        "py-src/experimentlens/agent/diagnostic_tools.py",
        "py-src/experimentlens/persistence/repository.py",
        "py-src/experimentlens/evaluation/",
        "src/App.tsx",
        ".github/workflows/ci.yml",
    ):
        assert source in content


def test_guide_published_numbers_match_machine_readable_baselines():
    content = GUIDE.read_text(encoding="utf-8")
    evaluation = json.loads(
        (ROOT / "evals" / "reports" / "baseline.json").read_text(encoding="utf-8")
    )
    reliability = json.loads(
        (ROOT / "docs" / "evidence" / "reliability-baseline.json").read_text(
            encoding="utf-8"
        )
    )

    assert evaluation["passed_count"] == evaluation["case_count"] == 30
    assert f"p95 为 {evaluation['p95_latency_ms']} ms" in content
    assert f"平均 Token {evaluation['average_tokens']}" in content
    assert reliability["configuration"]["run_count"] == 100
    assert reliability["results"]["completion_rate"] == 1
    assert reliability["results"]["duplicate_tool_calls"] == 0
    assert reliability["results"]["lost_events"] == 0
    assert reliability["results"]["sse_replay_failures"] == 0
    assert "100/100 完成" in content


def test_guide_local_markdown_links_resolve_and_readmes_link_to_it():
    content = GUIDE.read_text(encoding="utf-8")
    links = re.findall(r"\[[^]]+\]\(([^)]+)\)", content)
    local_links = [link.split("#", maxsplit=1)[0] for link in links if "://" not in link]

    assert local_links
    for link in local_links:
        assert (GUIDE.parent / link).resolve().exists(), f"broken guide link: {link}"

    assert "docs/onboarding-and-interview-study-guide.md" in (
        ROOT / "README.md"
    ).read_text(encoding="utf-8")
    assert "docs/onboarding-and-interview-study-guide.md" in (
        ROOT / "README_EN.md"
    ).read_text(encoding="utf-8")


def test_guide_does_not_encourage_misrepresenting_ownership():
    content = GUIDE.read_text(encoding="utf-8")

    assert "如实说明自己的贡献" in content
    assert "至少完成一个有测试、有 commit 的真实改动" in content
    assert "只写自己确实完成或接手验证过的部分" in content
