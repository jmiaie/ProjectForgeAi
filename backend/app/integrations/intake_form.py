from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from core.integrations_manager import IntegrationsManager


router = APIRouter(prefix="/intake", tags=["intake"])


class ConnectionRequest(BaseModel):
    connector_type: str = Field(..., examples=["google", "mcp_server"])
    auth_data: dict = Field(default_factory=dict)
    project_id: str | None = None


class OAuthStartRequest(BaseModel):
    connector_type: str = Field(..., examples=["google", "microsoft", "github"])
    project_id: str | None = None
    redirect_uri: str | None = None


class WebhookRegisterRequest(BaseModel):
    project_id: str
    webhook_url: str
    secret: str | None = None
    events: list[str] = Field(default_factory=lambda: ["project.updated", "automation.completed"])
    send_test: bool = False


def get_integrations_manager() -> IntegrationsManager:
    return IntegrationsManager()


@router.get("/connections/recommended")
async def recommended_connections(
    compliance: str = "standard",
    manager: IntegrationsManager = Depends(get_integrations_manager),
):
    connectors = await manager.get_recommended_connectors(compliance=compliance)
    return {"connectors": connectors}


@router.post("/connections/oauth/start")
async def start_oauth(
    data: OAuthStartRequest,
    manager: IntegrationsManager = Depends(get_integrations_manager),
):
    try:
        return await manager.start_oauth(data.connector_type, data.project_id, data.redirect_uri)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/oauth/{connector_type}/callback")
async def oauth_callback(
    connector_type: str,
    code: str = Query(...),
    state: str | None = None,
    project_id: str | None = None,
    manager: IntegrationsManager = Depends(get_integrations_manager),
):
    try:
        return await manager.connect(
            connector_type,
            {"code": code, "state": state},
            project_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/connections/webhook/register")
async def register_webhook(
    data: WebhookRegisterRequest,
    manager: IntegrationsManager = Depends(get_integrations_manager),
):
    try:
        return await manager.register_webhook(
            data.project_id,
            {
                "webhook_url": data.webhook_url,
                "secret": data.secret,
                "events": data.events,
            },
            send_test=data.send_test,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


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


@router.get("/connections/{project_id}")
async def list_connections(
    project_id: str,
    manager: IntegrationsManager = Depends(get_integrations_manager),
):
    return await manager.list_connections(project_id)


@router.get("/connections/{project_id}/{connector_type}/status")
async def connection_status(
    project_id: str,
    connector_type: str,
    manager: IntegrationsManager = Depends(get_integrations_manager),
):
    return await manager.connection_status(project_id, connector_type)


@router.get("/connections/{project_id}/{connector_type}/health")
async def connection_health(
    project_id: str,
    connector_type: str,
    manager: IntegrationsManager = Depends(get_integrations_manager),
):
    return await manager.health_check(project_id, connector_type)


@router.get("/connections/{project_id}/mcp/tools")
async def mcp_tools(
    project_id: str,
    connector_type: str = "mcp_server",
    manager: IntegrationsManager = Depends(get_integrations_manager),
):
    try:
        return await manager.discover_mcp_tools(project_id, connector_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
