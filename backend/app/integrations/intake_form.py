"""HTTP routes powering the Intake / Connections wizard."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.integrations_manager import IntegrationsManager

router = APIRouter(prefix="/intake", tags=["intake"])


def get_integrations_manager() -> IntegrationsManager:
    return IntegrationsManager()


class ConnectRequest(BaseModel):
    connector_type: str
    auth_data: dict[str, Any] = Field(default_factory=dict)
    project_id: str | None = None


@router.get("/connectors")
async def list_connectors(
    compliance: str = "standard",
    manager: IntegrationsManager = Depends(get_integrations_manager),
) -> dict[str, Any]:
    """Return all connectors recommended for the given compliance tier."""

    return {
        "compliance": compliance,
        "recommended": await manager.get_recommended_connectors(compliance=compliance),
        "all": await manager.list_connectors(),
    }


@router.post("/connections")
async def run_intake(
    payload: ConnectRequest,
    manager: IntegrationsManager = Depends(get_integrations_manager),
) -> dict[str, Any]:
    """Authenticate and persist a single connector."""

    try:
        return await manager.connect(
            connector_type=payload.connector_type,
            auth_data=payload.auth_data,
            project_id=payload.project_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
