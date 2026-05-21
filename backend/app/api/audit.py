"""Audit log query routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import AuditLogRepository
from app.db.session import fastapi_get_session

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/")
async def list_audit_entries(
    project_id: str | None = Query(default=None),
    action: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(fastapi_get_session),
) -> dict[str, Any]:
    repo = AuditLogRepository(session)
    entries = await repo.list(project_id=project_id, action=action, limit=limit)
    return {"items": [entry.to_dict() for entry in entries]}
