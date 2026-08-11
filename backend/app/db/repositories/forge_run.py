"""ForgeRun repository."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.forge_run import ForgeRun


class ForgeRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        project_id: str,
        recipe_id: str,
        spec: dict[str, Any],
        recipe_version: str | None = None,
        status: str = "pending",
    ) -> ForgeRun:
        run = ForgeRun(
            id=f"frun_{uuid.uuid4().hex[:16]}",
            project_id=project_id,
            recipe_id=recipe_id,
            recipe_version=recipe_version,
            spec=spec,
            status=status,
        )
        self.session.add(run)
        await self.session.flush()
        return run

    async def get(self, run_id: str) -> ForgeRun | None:
        return await self.session.get(ForgeRun, run_id)

    async def list_for_project(
        self, project_id: str, limit: int = 100, offset: int = 0
    ) -> list[ForgeRun]:
        stmt = (
            select(ForgeRun)
            .where(ForgeRun.project_id == project_id)
            .order_by(ForgeRun.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(
        self,
        run_id: str,
        *,
        status: str | None = None,
        manifest: dict[str, Any] | None = None,
        error: str | None = None,
        recipe_version: str | None = None,
    ) -> ForgeRun | None:
        run = await self.get(run_id)
        if run is None:
            return None
        if status is not None:
            run.status = status
        if manifest is not None:
            run.manifest = manifest
        if error is not None:
            run.error = error
        if recipe_version is not None:
            run.recipe_version = recipe_version
        await self.session.flush()
        return run
