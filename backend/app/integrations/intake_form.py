"""HTTP routes powering the Intake / Connections wizard."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.integrations_manager import IntegrationsManager
from app.db.repositories import AuditLogRepository, ConnectionRepository
from app.db.session import fastapi_get_session
from app.integrations.registry import ConnectorRegistry

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
    return {
        "compliance": compliance,
        "recommended": await manager.get_recommended_connectors(compliance=compliance),
        "all": await manager.list_connectors(),
    }


@router.post("/connections")
async def run_intake(
    payload: ConnectRequest,
    manager: IntegrationsManager = Depends(get_integrations_manager),
    session: AsyncSession = Depends(fastapi_get_session),
) -> dict[str, Any]:
    """Authenticate a connector and persist the resulting record."""

    try:
        result = await manager.connect(
            connector_type=payload.connector_type,
            auth_data=payload.auth_data,
            project_id=payload.project_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    metadata = ConnectorRegistry.get_metadata(payload.connector_type)
    secret_payload = _extract_secret(result.get("connection", {}))

    repo = ConnectionRepository(session)
    audit = AuditLogRepository(session)

    record = await repo.create(
        connector_type=payload.connector_type,
        auth_kind=metadata.get("type", "oauth"),
        provider=metadata.get("provider"),
        project_id=payload.project_id,
        scopes=metadata.get("scopes", []),
        secret=secret_payload,
        metadata={
            k: v
            for k, v in result.get("connection", {}).items()
            if k not in {"token", "code", "client"}
        },
        status=result.get("status", "connected"),
    )
    await audit.record(
        action="connection.created",
        project_id=payload.project_id,
        payload={
            "connector_type": payload.connector_type,
            "connection_id": record.id,
            "auth_kind": metadata.get("type"),
        },
    )
    await session.commit()

    return {
        "status": result.get("status", "connected"),
        "connector": payload.connector_type,
        "project_id": payload.project_id,
        "connection_id": record.id,
        "connection": record.to_dict(),
    }


@router.get("/connections")
async def list_connections(
    project_id: str | None = None,
    session: AsyncSession = Depends(fastapi_get_session),
) -> dict[str, Any]:
    repo = ConnectionRepository(session)
    records = (
        await repo.list_for_project(project_id)
        if project_id
        else await repo.list_all()
    )
    return {"items": [record.to_dict() for record in records]}


def _extract_secret(connection: dict[str, Any]) -> str | None:
    """Pull the most-sensitive blob out of a connector response for storage."""

    for key in ("token", "code"):
        value = connection.get(key)
        if isinstance(value, str) and value:
            return value
    if connection.get("client") is not None:
        return json.dumps({"server_url": connection.get("server_url")})
    return None
