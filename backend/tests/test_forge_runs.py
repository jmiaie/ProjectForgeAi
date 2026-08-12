"""Tests for /api/v1/forge/runs endpoints and ForgeService."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.agents.forge_service import (
    LocalForgeExecutor,
    PathTraversalError,
    UnresolvedVariableError,
)
from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_project(name: str = "test-proj") -> str:
    """Create a project via the API and return its project_id."""
    res = client.post("/api/v1/projects/", data={"name": name, "compliance": "standard"})
    assert res.status_code == 200, res.text
    return res.json()["project_id"]


# ---------------------------------------------------------------------------
# API: POST /forge/runs – happy path
# ---------------------------------------------------------------------------

def test_forge_run_create_happy_path() -> None:
    project_id = _create_project("forge-happy")
    body = {
        "project_id": project_id,
        "spec": {
            "projectName": "forge-happy",
            "recipe": "minimal",
        },
    }
    res = client.post("/api/v1/forge/runs", json=body)
    assert res.status_code == 202, res.text
    data = res.json()
    assert data["project_id"] == project_id
    assert data["status"] == "completed"
    assert data["recipe_id"] == "minimal"
    assert data["recipe_version"] is not None
    assert data["manifest"] is not None
    assert isinstance(data["manifest"]["files"], list)
    assert data["error"] is None
    assert data["created_at"] is not None
    assert data["id"].startswith("frun_")


# ---------------------------------------------------------------------------
# API: GET /forge/runs/{run_id}
# ---------------------------------------------------------------------------

def test_forge_run_get() -> None:
    project_id = _create_project("forge-get")
    body = {
        "project_id": project_id,
        "spec": {"projectName": "forge-get", "recipe": "minimal"},
    }
    run_id = client.post("/api/v1/forge/runs", json=body).json()["id"]

    res = client.get(f"/api/v1/forge/runs/{run_id}")
    assert res.status_code == 200
    assert res.json()["id"] == run_id


def test_forge_run_get_not_found() -> None:
    res = client.get("/api/v1/forge/runs/nonexistent-run-id")
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# API: GET /forge/runs?project_id=...
# ---------------------------------------------------------------------------

def test_forge_run_list() -> None:
    project_id = _create_project("forge-list")
    for _ in range(2):
        client.post(
            "/api/v1/forge/runs",
            json={"project_id": project_id, "spec": {"projectName": "forge-list", "recipe": "minimal"}},
        )
    res = client.get(f"/api/v1/forge/runs?project_id={project_id}")
    assert res.status_code == 200
    assert len(res.json()) == 2


# ---------------------------------------------------------------------------
# API: missing project → 404
# ---------------------------------------------------------------------------

def test_forge_run_missing_project() -> None:
    res = client.post(
        "/api/v1/forge/runs",
        json={
            "project_id": "proj_does_not_exist",
            "spec": {"projectName": "x-proj", "recipe": "minimal"},
        },
    )
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# API: invalid recipe → run stored as failed
# ---------------------------------------------------------------------------

def test_forge_run_invalid_recipe_stored_as_failed() -> None:
    project_id = _create_project("forge-fail")
    res = client.post(
        "/api/v1/forge/runs",
        json={
            "project_id": project_id,
            "spec": {"projectName": "forge-fail", "recipe": "no-such-recipe"},
        },
    )
    assert res.status_code == 202
    data = res.json()
    assert data["status"] == "failed"
    assert data["error"] is not None
    assert "no-such-recipe" in data["error"] or "not found" in data["error"].lower()


# ---------------------------------------------------------------------------
# API: invalid spec (missing recipe field) → 422
# ---------------------------------------------------------------------------

def test_forge_run_invalid_spec_missing_recipe() -> None:
    res = client.post(
        "/api/v1/forge/runs",
        json={"project_id": "any-id", "spec": {"projectName": "bad"}},
    )
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# API: response shape contract
# ---------------------------------------------------------------------------

def test_forge_run_response_shape() -> None:
    project_id = _create_project("forge-shape")
    res = client.post(
        "/api/v1/forge/runs",
        json={"project_id": project_id, "spec": {"projectName": "forge-shape", "recipe": "minimal"}},
    )
    data = res.json()
    required_keys = {
        "id", "project_id", "status", "recipe_id", "recipe_version",
        "spec", "manifest", "error", "created_at", "updated_at",
    }
    assert required_keys <= data.keys()


# ---------------------------------------------------------------------------
# Unit: LocalForgeExecutor.substitute_vars – fail on unresolved
# ---------------------------------------------------------------------------

def test_local_executor_substitute_vars_raises_on_unresolved() -> None:
    executor = LocalForgeExecutor()
    with pytest.raises(UnresolvedVariableError, match="unknownVar"):
        executor.substitute_vars("hello {{unknownVar}}", {"other": "value"})


def test_local_executor_substitute_vars_resolves_known() -> None:
    executor = LocalForgeExecutor()
    result = executor.substitute_vars("Hello {{name}}!", {"name": "world"})
    assert result == "Hello world!"


# ---------------------------------------------------------------------------
# Unit: LocalForgeExecutor.safe_output_path – path traversal
# ---------------------------------------------------------------------------

def test_safe_output_path_traversal_raises() -> None:
    from pathlib import Path

    executor = LocalForgeExecutor()
    with pytest.raises(PathTraversalError):
        executor.safe_output_path(Path("/tmp/output"), "../../../etc/passwd")


def test_safe_output_path_normal() -> None:
    from pathlib import Path

    executor = LocalForgeExecutor()
    result = executor.safe_output_path(Path("/tmp/output"), "src/index.js")
    assert str(result).endswith("src/index.js")
