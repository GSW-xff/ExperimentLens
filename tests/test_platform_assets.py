from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]


def test_compose_declares_durable_platform_and_health_checks():
    compose = yaml.safe_load((ROOT / "compose.yaml").read_text(encoding="utf-8"))
    services = compose["services"]
    assert {
        "api", "worker", "postgres", "redis", "minio", "temporal", "temporal-ui",
        "otel-collector", "prometheus", "grafana",
    } <= set(services)
    assert "HEALTHCHECK" in (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert services["postgres"]["healthcheck"]
    assert services["redis"]["healthcheck"]
    assert services["api"]["read_only"] is True
    assert services["worker"]["read_only"] is True
    assert "experimentlens-worker" in " ".join(services["worker"]["command"])


def test_ci_enforces_tests_coverage_build_and_container():
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
    jobs = workflow["jobs"]
    assert {"python", "web", "container", "security"} <= set(jobs)
    rendered = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "--cov-fail-under=85" in rendered
    assert "pnpm test" in rendered
    assert "docker/build-push-action" in rendered


def test_reproducible_verification_and_demo_scripts_cover_upgrade_gates():
    verify = (ROOT / "scripts/verify.sh").read_text(encoding="utf-8")
    demo = (ROOT / "scripts/interview_demo.sh").read_text(encoding="utf-8")

    for marker in (
        "pytest --cov", "ruff check", "vitest run", "tsc -b", "vite build",
        "alembic upgrade head", "alembic downgrade base",
    ):
        assert marker in verify
    assert "experimentlens-worker" in demo
    assert "experimentlens-eval" in demo
    assert "experimentlens-benchmark --runs 100 --workers 2" in demo
