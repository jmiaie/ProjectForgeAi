"""Automation HTTP routes."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.automations.engine import get_workflow_engine
from app.automations.kinds import AUTOMATION_KINDS, get_automation_kind
from app.automations.schedule import compute_next_run
from app.db.repositories import (
    AuditLogRepository,
    AutomationRepository,
    ProjectRepository,
)
from app.db.session import fastapi_get_session

router = APIRouter(
    prefix="/projects/{project_id}/automations",
    tags=["automations"],
)


class AutomationCreate(BaseModel):
    kind: str
    interval_seconds: int | None = Field(default=None, ge=10)
    cron: str | None = None
    max_runs: int | None = Field(default=None, ge=1)
    config: dict[str, Any] = Field(default_factory=dict)
    start_now: bool = False


class AutomationKindsRouter(APIRouter):
    pass


catalogue_router = APIRouter(prefix="/automations", tags=["automations"])


@catalogue_router.get("/kinds")
async def list_automation_kinds() -> dict[str, Any]:
    return {
        "kinds": [
            {
                "name": kind.name,
                "description": kind.description,
                "default_interval_seconds": kind.default_interval_seconds,
                "specialist": kind.specialist,
            }
            for kind in AUTOMATION_KINDS.values()
        ]
    }


@router.post("/")
async def create_automation(
    project_id: str,
    payload: AutomationCreate,
    session: AsyncSession = Depends(fastapi_get_session),
) -> dict[str, Any]:
    projects = ProjectRepository(session)
    project = await projects.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        kind = get_automation_kind(payload.kind)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    interval = payload.interval_seconds or kind.default_interval_seconds
    now = datetime.now(timezone.utc)
    next_run = compute_next_run(
        interval_seconds=interval,
        cron=payload.cron,
        last_run_at=now if not payload.start_now else None,
        now=now,
    )

    repo = AutomationRepository(session)
    automation = await repo.create(
        kind=kind.name,
        project_id=project_id,
        interval_seconds=interval,
        cron=payload.cron,
        max_runs=payload.max_runs,
        next_run_at=next_run,
        config=payload.config,
    )

    engine = get_workflow_engine()
    handle = await engine.schedule(automation)
    if handle is not None:
        automation.workflow_handle = handle
        await session.flush()

    audit = AuditLogRepository(session)
    await audit.record(
        action="automation.created",
        project_id=project_id,
        payload={"automation_id": automation.id, "kind": automation.kind},
    )
    await session.commit()

    return automation.to_dict()


@router.get("/")
async def list_automations(
    project_id: str,
    status: str | None = None,
    session: AsyncSession = Depends(fastapi_get_session),
) -> dict[str, Any]:
    repo = AutomationRepository(session)
    rows = await repo.list_for_project(project_id, status=status)
    return {"items": [row.to_dict() for row in rows]}


@router.get("/{automation_id}")
async def get_automation(
    project_id: str,
    automation_id: str,
    session: AsyncSession = Depends(fastapi_get_session),
) -> dict[str, Any]:
    repo = AutomationRepository(session)
    automation = await repo.get(automation_id)
    if automation is None or automation.project_id != project_id:
        raise HTTPException(status_code=404, detail="Automation not found")
    return automation.to_dict()


@router.post("/{automation_id}/run-now")
async def run_now(
    project_id: str,
    automation_id: str,
    session: AsyncSession = Depends(fastapi_get_session),
) -> dict[str, Any]:
    repo = AutomationRepository(session)
    automation = await repo.get(automation_id)
    if automation is None or automation.project_id != project_id:
        raise HTTPException(status_code=404, detail="Automation not found")

    engine = get_workflow_engine()
    return await engine.trigger_now(automation_id)


@router.delete("/{automation_id}")
async def cancel_automation(
    project_id: str,
    automation_id: str,
    session: AsyncSession = Depends(fastapi_get_session),
) -> dict[str, Any]:
    repo = AutomationRepository(session)
    automation = await repo.get(automation_id)
    if automation is None or automation.project_id != project_id:
        raise HTTPException(status_code=404, detail="Automation not found")

    engine = get_workflow_engine()
    await engine.cancel(automation)
    cancelled = await repo.cancel(automation)

    audit = AuditLogRepository(session)
    await audit.record(
        action="automation.cancelled",
        project_id=project_id,
        payload={"automation_id": automation.id, "kind": automation.kind},
    )
    await session.commit()

    return cancelled.to_dict()
