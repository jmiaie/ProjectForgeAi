"""Forge spec validation, planning, and run API."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from jsonschema import Draft7Validator
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.forge_service import (
    ForgeService,
    InvalidSpecError,
    ProjectNotFoundError,
)
from app.db.session import fastapi_get_session

router = APIRouter(prefix="/forge", tags=["forge"])

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCHEMA_PATH = _REPO_ROOT / "schemas" / "forge-spec.schema.json"


class ForgeSpec(BaseModel):
    projectName: str = Field(pattern=r"^[a-z][a-z0-9-]*$", max_length=64)
    recipe: str
    description: str | None = Field(default=None, max_length=500)
    port: int | None = Field(default=None, ge=1024, le=65535)


class ForgePlanResponse(BaseModel):
    recipe: str
    projectName: str
    vars: dict[str, str]


class ForgeRunRequest(BaseModel):
    """Request body for creating a new Forge run."""

    project_id: str = Field(min_length=1, max_length=64)
    spec: ForgeSpec


class ForgeRunResponse(BaseModel):
    """API response shape for a Forge run."""

    id: str
    project_id: str
    status: str
    recipe_id: str
    recipe_version: str | None
    spec: dict[str, Any]
    manifest: dict[str, Any] | None
    error: str | None
    created_at: str | None
    updated_at: str | None


def _load_schema() -> dict[str, Any]:
    if not _SCHEMA_PATH.is_file():
        raise HTTPException(
            status_code=503,
            detail=f"Forge schema not found at {_SCHEMA_PATH}",
        )
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


def _validate_spec_dict(data: dict[str, Any]) -> ForgeSpec:
    schema = _load_schema()
    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
    if errors:
        detail = "; ".join(
            f"{'/'.join(str(p) for p in err.path) or '/'} {err.message}"
            for err in errors
        )
        raise HTTPException(status_code=422, detail=f"Spec validation failed: {detail}")
    return ForgeSpec.model_validate(data)


def _plan(spec: ForgeSpec) -> ForgePlanResponse:
    port = spec.port or (3000 if spec.recipe == "express-api" else 0)
    return ForgePlanResponse(
        recipe=spec.recipe,
        projectName=spec.projectName,
        vars={
            "projectName": spec.projectName,
            "description": spec.description or "",
            "port": str(port),
        },
    )


@router.post("/validate")
async def validate_forge_spec(spec: ForgeSpec) -> dict[str, str]:
    """Validate a forge spec (Pydantic + JSON Schema)."""
    data = spec.model_dump(exclude_none=True)
    _validate_spec_dict(data)
    return {"status": "ok", "recipe": spec.recipe, "projectName": spec.projectName}


@router.post("/plan")
async def plan_forge_spec(spec: ForgeSpec) -> ForgePlanResponse:
    """Return template variables for a validated spec."""
    data = spec.model_dump(exclude_none=True)
    validated = _validate_spec_dict(data)
    return _plan(validated)


@router.post("/runs", status_code=202)
async def create_forge_run(
    body: ForgeRunRequest,
    session: AsyncSession = Depends(fastapi_get_session),
) -> ForgeRunResponse:
    """Create and immediately execute a Forge run for a project.

    Returns 202 Accepted with the completed (or failed) run record so callers
    can inspect the result synchronously. A background/async variant can be
    added later without changing this contract.
    """
    spec_dict = body.spec.model_dump(exclude_none=True)
    svc = ForgeService(session)
    try:
        run = await svc.create_run(project_id=body.project_id, spec=spec_dict)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidSpecError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ForgeRunResponse(**run.to_dict())


@router.get("/runs/{run_id}")
async def get_forge_run(
    run_id: str,
    session: AsyncSession = Depends(fastapi_get_session),
) -> ForgeRunResponse:
    """Retrieve a Forge run by ID."""
    svc = ForgeService(session)
    run = await svc.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Forge run {run_id!r} not found")
    return ForgeRunResponse(**run.to_dict())


@router.get("/runs")
async def list_forge_runs(
    project_id: str,
    session: AsyncSession = Depends(fastapi_get_session),
) -> list[ForgeRunResponse]:
    """List all Forge runs for a project."""
    svc = ForgeService(session)
    runs = await svc.list_runs(project_id)
    return [ForgeRunResponse(**r.to_dict()) for r in runs]
