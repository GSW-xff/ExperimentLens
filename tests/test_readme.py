import json
import re
from pathlib import Path

ROOT = Path(__file__).parents[1]
README = ROOT / "README.md"
README_EN = ROOT / "README_EN.md"


def test_readmes_link_to_each_language():
    chinese = README.read_text(encoding="utf-8")
    english = README_EN.read_text(encoding="utf-8")

    assert "[English](README_EN.md)" in chinese
    assert "[简体中文](README.md)" in english


def test_english_readme_covers_the_public_project_story():
    content = README_EN.read_text(encoding="utf-8")

    for section in (
        "## Highlights",
        "## Published Baselines",
        "## Architecture",
        "## Quick Start",
        "## Agent Runtime",
        "## Evaluation and Reliability",
        "## Full Verification",
        "## Current Boundaries",
    ):
        assert section in content

    for marker in (
        "experimentlens-api",
        "experimentlens-worker",
        "experimentlens-eval",
        "experimentlens-benchmark --runs 100 --workers 2",
        "Lease + fencing token",
        "EvidenceRef",
        "make verify",
    ):
        assert marker in content


def test_published_readme_metrics_match_machine_readable_baselines():
    content = README_EN.read_text(encoding="utf-8")
    evaluation = json.loads(
        (ROOT / "evals/reports/baseline.json").read_text(encoding="utf-8")
    )
    reliability = json.loads(
        (ROOT / "docs/evidence/reliability-baseline.json").read_text(encoding="utf-8")
    )

    case_count = evaluation["case_count"]
    run_count = reliability["configuration"]["run_count"]
    results = reliability["results"]

    assert evaluation["passed_count"] == case_count
    assert f"{case_count}/{case_count} cases passed" in content
    assert results["completion_rate"] == 1
    assert f"{run_count}/{run_count} runs completed" in content
    assert f"| Duplicate tool calls | {results['duplicate_tool_calls']} |" in content
    assert f"| Lost events | {results['lost_events']} |" in content
    assert f"| SSE replay failures | {results['sse_replay_failures']} |" in content


def test_english_readme_local_links_resolve():
    content = README_EN.read_text(encoding="utf-8")
    links = re.findall(r"\[[^]]+\]\(([^)]+)\)", content)
    local_links = [link.split("#", maxsplit=1)[0] for link in links if "://" not in link]

    assert local_links
    for link in local_links:
        assert (ROOT / link).exists(), f"README_EN.md contains a broken link: {link}"
