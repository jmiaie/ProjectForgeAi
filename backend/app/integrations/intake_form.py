from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.integrations_manager import IntegrationsManager


router = APIRouter(prefix="/intake", tags=["intake"])


class ConnectionRequest(BaseModel):
    connector_type: str = Field(..., examples=["google", "mcp_server"])
    auth_data: dict = Field(default_factory=dict)
    project_id: str | None = None


def get_integrations_manager() -> IntegrationsManager:
    return IntegrationsManager()


@router.get("/connections/recommended")
async def recommended_connections(
    compliance: str = "standard",
    manager: IntegrationsManager = Depends(get_integrations_manager),
):
    connectors = await manager.get_recommended_connectors(compliance=compliance)
    return {"connectors": connectors}


@router.post("/connections")
async def run_intake(
    data: ConnectionRequest,
    manager: IntegrationsManager = Depends(get_integrations_manager),
):
    try:
        return await manager.connect(
            data.connector_type,
            data.auth_data,
            data.project_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
