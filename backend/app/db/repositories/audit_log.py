"""Audit log repository."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditLog


class AuditLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def record(
        self,
        *,
        action: str,
        actor: str = "system",
        project_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            id=f"audit_{uuid.uuid4().hex[:16]}",
            project_id=project_id,
            actor=actor,
            action=action,
            payload=payload or {},
        )
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def list(
        self,
        *,
        project_id: str | None = None,
        action: str | None = None,
        limit: int = 100,
    ) -> list[AuditLog]:
        stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
        if project_id is not None:
            stmt = stmt.where(AuditLog.project_id == project_id)
        if action is not None:
            stmt = stmt.where(AuditLog.action == action)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
