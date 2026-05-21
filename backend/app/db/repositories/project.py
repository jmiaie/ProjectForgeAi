"""Project repository."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Project


class ProjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        project_id: str,
        name: str,
        compliance: str = "standard",
        objective: str | None = None,
        status: str = "created",
        metadata: dict[str, Any] | None = None,
        organization_id: str | None = None,
        created_by_user_id: str | None = None,
    ) -> Project:
        project = Project(
            id=project_id,
            name=name,
            compliance=compliance,
            objective=objective,
            status=status,
            project_metadata=metadata or {},
            organization_id=organization_id,
            created_by_user_id=created_by_user_id,
        )
        self.session.add(project)
        await self.session.flush()
        return project

    async def get(self, project_id: str) -> Project | None:
        return await self.session.get(Project, project_id)

    async def list(self, limit: int = 100, offset: int = 0) -> list[Project]:
        stmt = (
            select(Project)
            .order_by(Project.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(self, project_id: str, status: str) -> Project | None:
        project = await self.get(project_id)
        if project is None:
            return None
        project.status = status
        await self.session.flush()
        return project

    async def merge_metadata(
        self, project_id: str, patch: dict[str, Any]
    ) -> Project | None:
        project = await self.get(project_id)
        if project is None:
            return None
        merged = {**(project.project_metadata or {}), **patch}
        project.project_metadata = merged
        await self.session.flush()
        return project

    async def delete(self, project: Project) -> None:
        await self.session.delete(project)
        await self.session.flush()
