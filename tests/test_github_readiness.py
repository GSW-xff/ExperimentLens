from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]


def test_public_repository_has_governance_and_release_documents():
    required_files = (
        "LICENSE",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "CODE_OF_CONDUCT.md",
        "docs/github-release-checklist.md",
        ".github/PULL_REQUEST_TEMPLATE.md",
        ".github/ISSUE_TEMPLATE/bug_report.yml",
        ".github/ISSUE_TEMPLATE/feature_request.yml",
    )

    for relative_path in required_files:
        path = ROOT / relative_path
        assert path.is_file(), f"Missing public repository file: {relative_path}"
        assert path.stat().st_size > 100, f"Public repository file is too small: {relative_path}"

    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "MIT License" in license_text
    assert "Permission is hereby granted" in license_text


def test_local_state_and_secrets_are_excluded_but_example_is_publishable():
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()

    for marker in (".DS_Store", ".env", ".experimentlens/", "node_modules/"):
        assert marker in gitignore
    for marker in (".env", ".experimentlens", "node_modules"):
        assert marker in dockerignore
    assert "!.env.example" in gitignore
    assert "!.env.example" in dockerignore

    example = (ROOT / ".env.example").read_text(encoding="utf-8")
    for variable in (
        "EXPERIMENTLENS_DATABASE_URL",
        "EXPERIMENTLENS_WORKSPACE",
        "EXPERIMENTLENS_AGENT_MAX_STEPS",
        "OPENAI_API_KEY=",
    ):
        assert variable in example
    assert "sk-" not in example


def test_github_forms_and_dependency_updates_are_valid_yaml():
    issue_templates = (
        ROOT / ".github/ISSUE_TEMPLATE/bug_report.yml",
        ROOT / ".github/ISSUE_TEMPLATE/feature_request.yml",
    )
    for path in issue_templates:
        form = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert form["name"]
        assert form["description"]
        assert form["body"]

    dependabot = yaml.safe_load(
        (ROOT / ".github/dependabot.yml").read_text(encoding="utf-8")
    )
    ecosystems = {entry["package-ecosystem"] for entry in dependabot["updates"]}
    assert dependabot["version"] == 2
    assert {"pip", "npm", "github-actions", "docker"} <= ecosystems


def test_runtime_version_files_are_used_by_ci_and_documented():
    assert (ROOT / ".python-version").read_text(encoding="utf-8").strip() == "3.12"
    assert (ROOT / ".nvmrc").read_text(encoding="utf-8").strip().startswith("22.")

    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "python-version-file: .python-version" in workflow
    assert "node-version-file: .nvmrc" in workflow
    assert "workflow_dispatch:" in workflow

    for readme_name in ("README.md", "README_EN.md"):
        readme = (ROOT / readme_name).read_text(encoding="utf-8")
        assert ".env.example" in readme
        assert "CONTRIBUTING.md" in readme
        assert "SECURITY.md" in readme
