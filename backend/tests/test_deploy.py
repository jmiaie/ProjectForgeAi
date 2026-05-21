"""Validate deployment manifests (Helm chart, compose, scripts)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
CHART = ROOT / "deploy" / "helm" / "projectforge"


REQUIRED_CHART_FILES = [
    "Chart.yaml",
    "values.yaml",
    "values-saas.yaml",
    "values-hybrid.yaml",
    "values-onprem.yaml",
    "templates/_helpers.tpl",
    "templates/deployment-backend.yaml",
    "templates/service-backend.yaml",
    "templates/configmap.yaml",
    "templates/secret.yaml",
    "templates/job-migrate.yaml",
    "templates/postgresql.yaml",
    "templates/redis.yaml",
    "templates/neo4j.yaml",
    "templates/ingress.yaml",
]


def test_helm_chart_files_exist() -> None:
    for rel in REQUIRED_CHART_FILES:
        assert (CHART / rel).is_file(), f"missing {rel}"


def test_chart_yaml_is_valid() -> None:
    meta = yaml.safe_load((CHART / "Chart.yaml").read_text())
    assert meta["name"] == "projectforge"
    assert meta["apiVersion"] == "v2"


def test_values_overlays_parse() -> None:
    for name in ("values.yaml", "values-saas.yaml", "values-hybrid.yaml", "values-onprem.yaml"):
        data = yaml.safe_load((CHART / name).read_text())
        assert isinstance(data, dict)
        assert "backend" in data or "global" in data


def test_docker_compose_prod_parses() -> None:
    compose = yaml.safe_load((ROOT / "docker-compose.prod.yml").read_text())
    assert "backend" in compose["services"]
    assert compose["services"]["backend"].get("healthcheck")


def test_entrypoint_script_exists_and_is_executable() -> None:
    entrypoint = ROOT / "backend" / "scripts" / "entrypoint.sh"
    assert entrypoint.is_file()
    content = entrypoint.read_text()
    assert "alembic upgrade head" in content
    assert entrypoint.stat().st_mode & 0o111, "entrypoint should be executable"


def test_onprem_scripts_exist() -> None:
    for name in ("bundle-images.sh", "load-images.sh", "install.sh"):
        path = ROOT / "deploy" / "onprem" / name
        assert path.is_file(), name


@pytest.mark.skipif(shutil.which("helm") is None, reason="helm not installed")
def test_helm_template_renders_default_profile() -> None:
    result = subprocess.run(
        [
            "helm",
            "template",
            "test-release",
            str(CHART),
            "--set",
            "secrets.encryptionKey=test-enc",
            "--set",
            "secrets.jwtSecret=test-jwt",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    rendered = result.stdout
    assert "kind: Deployment" in rendered
    assert "-backend" in rendered
    assert "kind: Job" in rendered
    assert "alembic" in rendered and "upgrade" in rendered


@pytest.mark.skipif(shutil.which("helm") is None, reason="helm not installed")
def test_helm_template_onprem_profile() -> None:
    result = subprocess.run(
        [
            "helm",
            "template",
            "onprem",
            str(CHART),
            "-f",
            str(CHART / "values-onprem.yaml"),
            "--set",
            "global.imageRegistry=registry.local/projectforge",
            "--set",
            "secrets.encryptionKey=test-enc",
            "--set",
            "secrets.jwtSecret=test-jwt",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "deploymentMode: onprem" in result.stdout or "onprem" in result.stdout
