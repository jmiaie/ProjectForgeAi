"""Automation repository."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Automation


class AutomationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        kind: str,
        project_id: str | None,
        interval_seconds: int | None = None,
        cron: str | None = None,
        max_runs: int | None = None,
        next_run_at: datetime | None = None,
        config: dict[str, Any] | None = None,
        workflow_handle: str | None = None,
        status: str = "active",
    ) -> Automation:
        record = Automation(
            id=f"auto_{uuid.uuid4().hex[:16]}",
            project_id=project_id,
            kind=kind,
            status=status,
            interval_seconds=interval_seconds,
            cron=cron,
            max_runs=max_runs,
            next_run_at=next_run_at,
            config=config or {},
            workflow_handle=workflow_handle,
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def get(self, automation_id: str) -> Automation | None:
        return await self.session.get(Automation, automation_id)

    async def list_for_project(
        self, project_id: str, status: str | None = None
    ) -> list[Automation]:
        stmt = (
            select(Automation)
            .where(Automation.project_id == project_id)
            .order_by(Automation.created_at.desc())
        )
        if status:
            stmt = stmt.where(Automation.status == status)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_due(self, now: datetime, limit: int = 50) -> list[Automation]:
        stmt = (
            select(Automation)
            .where(Automation.status == "active")
            .where(Automation.next_run_at.is_not(None))
            .where(Automation.next_run_at <= now)
            .order_by(Automation.next_run_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_after_run(
        self,
        automation: Automation,
        *,
        last_run_at: datetime,
        next_run_at: datetime | None,
    ) -> Automation:
        automation.last_run_at = last_run_at
        automation.runs_completed = (automation.runs_completed or 0) + 1
        automation.next_run_at = next_run_at
        if (
            automation.max_runs is not None
            and automation.runs_completed >= automation.max_runs
        ):
            automation.status = "completed"
            automation.next_run_at = None
        await self.session.flush()
        return automation

    async def cancel(self, automation: Automation) -> Automation:
        automation.status = "cancelled"
        automation.next_run_at = None
        await self.session.flush()
        return automation
