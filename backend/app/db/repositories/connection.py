"""Connection repository."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Connection
from app.security import encrypt_text


class ConnectionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        connector_type: str,
        auth_kind: str,
        provider: str | None = None,
        project_id: str | None = None,
        scopes: list[str] | None = None,
        secret: str | None = None,
        metadata: dict[str, Any] | None = None,
        status: str = "connected",
    ) -> Connection:
        connection = Connection(
            id=f"conn_{uuid.uuid4().hex[:16]}",
            project_id=project_id,
            connector_type=connector_type,
            provider=provider,
            auth_kind=auth_kind,
            scopes=scopes or [],
            encrypted_secret=encrypt_text(secret) if secret else None,
            connection_metadata=metadata or {},
            status=status,
        )
        self.session.add(connection)
        await self.session.flush()
        return connection

    async def get(self, connection_id: str) -> Connection | None:
        return await self.session.get(Connection, connection_id)

    async def list_for_project(self, project_id: str) -> list[Connection]:
        stmt = (
            select(Connection)
            .where(Connection.project_id == project_id)
            .order_by(Connection.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_all(self, limit: int = 200) -> list[Connection]:
        stmt = select(Connection).order_by(Connection.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
