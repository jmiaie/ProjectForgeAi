"""Audit log query routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_authenticated_user
from app.db.repositories import AuditLogRepository
from app.db.session import fastapi_get_session

# Authentication only. Entries are NOT yet scoped to the caller's
# organisations -- see docs/ROADMAP.md (P0 backend authorization).
router = APIRouter(
    prefix="/audit",
    tags=["audit"],
    dependencies=[Depends(require_authenticated_user)],
)


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
