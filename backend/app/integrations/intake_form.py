from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, HttpUrl

from app.core.integrations_manager import IntegrationsManager

router = APIRouter()
_manager = IntegrationsManager()


class GenericConnectRequest(BaseModel):
    connector_type: str
    project_id: str | None = None
    auth_data: dict


class OAuthStartRequest(BaseModel):
    connector_type: str
    project_id: str | None = None
    redirect_uri: HttpUrl


class OAuthCallbackRequest(BaseModel):
    connector_type: str
    project_id: str | None = None
    state: str
    code: str
    redirect_uri: HttpUrl


class APIKeyConnectRequest(BaseModel):
    connector_type: str
    project_id: str | None = None
    api_key: str


class MCPConnectRequest(BaseModel):
    server_url: HttpUrl
    project_id: str | None = None
    token: str | None = None
    connector_type: str = "mcp_server"


def get_integrations_manager() -> IntegrationsManager:
    return _manager


@router.get("/intake/recommended")
async def recommended_connectors(
    project_id: str | None = Query(default=None),
    manager: IntegrationsManager = Depends(get_integrations_manager),
) -> dict:
    return await manager.get_recommended_connectors(project_id=project_id)


@router.get("/intake/connections")
async def list_connections(
    project_id: str | None = Query(default=None),
    manager: IntegrationsManager = Depends(get_integrations_manager),
) -> dict:
    return await manager.list_connections(project_id=project_id)


@router.post("/intake/oauth/start")
async def start_oauth(
    request: OAuthStartRequest,
    manager: IntegrationsManager = Depends(get_integrations_manager),
) -> dict:
    try:
        return await manager.begin_oauth(
            connector_type=request.connector_type,
            project_id=request.project_id,
            redirect_uri=str(request.redirect_uri),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/intake/oauth/callback")
async def oauth_callback(
    request: OAuthCallbackRequest,
    manager: IntegrationsManager = Depends(get_integrations_manager),
) -> dict:
    try:
        return await manager.complete_oauth(
            connector_type=request.connector_type,
            project_id=request.project_id,
            state=request.state,
            code=request.code,
            redirect_uri=str(request.redirect_uri),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/intake/api-key")
async def connect_api_key(
    request: APIKeyConnectRequest,
    manager: IntegrationsManager = Depends(get_integrations_manager),
) -> dict:
    try:
        return await manager.connect_api_key(
            connector_type=request.connector_type,
            project_id=request.project_id,
            api_key=request.api_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/intake/mcp")
async def connect_mcp(
    request: MCPConnectRequest,
    manager: IntegrationsManager = Depends(get_integrations_manager),
) -> dict:
    try:
        return await manager.connect_mcp(
            project_id=request.project_id,
            server_url=str(request.server_url),
            token=request.token,
            connector_type=request.connector_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/intake/connections")
async def run_intake(
    request: GenericConnectRequest,
    manager: IntegrationsManager = Depends(get_integrations_manager),
) -> dict:
    try:
        return await manager.connect(
            connector_type=request.connector_type,
            auth_data=request.auth_data,
            project_id=request.project_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
