"""Forge spec validation and planning API (mirrors TypeScript planner)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from jsonschema import Draft7Validator
from pydantic import BaseModel, Field

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
