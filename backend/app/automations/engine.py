"""Workflow engine abstractions.

Two implementations behind one async interface:

* :class:`InMemoryWorkflowEngine` — fully in-process scheduler that polls
  the ``automations`` table and runs due jobs. Persists nothing of its own
  beyond the DB row, so it is safe to start/stop alongside the API.
* :class:`TemporalWorkflowEngine` — submits a Temporal schedule per
  automation. Requires the ``temporalio`` SDK and a reachable server.

The factory :func:`get_workflow_engine` selects between them based on
``Settings.WORKFLOW_BACKEND``.
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from app.automations.runner import AutomationRunner
from app.core.config import Settings, get_settings
from app.db.models import Automation
from app.db.repositories import AutomationRepository
from app.db.session import get_session

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------
class WorkflowEngine(ABC):
    backend: str = "abstract"

    @abstractmethod
    async def schedule(self, automation: Automation) -> str | None: ...

    @abstractmethod
    async def cancel(self, automation: Automation) -> None: ...

    async def trigger_now(self, automation_id: str) -> dict[str, Any]:
        runner = AutomationRunner()
        return await runner.run(automation_id)

    async def start(self) -> None:  # pragma: no cover - default no-op
        return None

    async def stop(self) -> None:  # pragma: no cover - default no-op
        return None


# ---------------------------------------------------------------------------
# In-memory polling engine
# ---------------------------------------------------------------------------
class InMemoryWorkflowEngine(WorkflowEngine):
    backend = "memory"

    def __init__(self, poll_interval_seconds: float = 5.0) -> None:
        self.poll_interval_seconds = poll_interval_seconds
        self._task: asyncio.Task[None] | None = None
        self._stopping = asyncio.Event()

    async def schedule(self, automation: Automation) -> str | None:
        return f"inmem_{automation.id}"

    async def cancel(self, automation: Automation) -> None:
        return None

    async def start(self) -> None:
        if self._task is not None:
            return
        self._stopping.clear()
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        if self._task is None:
            return
        self._stopping.set()
        try:
            await asyncio.wait_for(self._task, timeout=self.poll_interval_seconds + 1)
        except asyncio.TimeoutError:  # pragma: no cover - defensive
            self._task.cancel()
        self._task = None

    async def _run_loop(self) -> None:  # pragma: no cover - exercised manually
        runner = AutomationRunner()
        while not self._stopping.is_set():
            try:
                await self._tick(runner)
            except Exception as exc:
                logger.exception("Automation tick failed: %s", exc)
            try:
                await asyncio.wait_for(
                    self._stopping.wait(), timeout=self.poll_interval_seconds
                )
            except asyncio.TimeoutError:
                continue

    async def _tick(self, runner: AutomationRunner) -> None:
        async with get_session() as session:
            repo = AutomationRepository(session)
            due = await repo.list_due(datetime.now(timezone.utc))
            ids = [row.id for row in due]
        for automation_id in ids:
            try:
                await runner.run(automation_id)
            except Exception as exc:
                logger.exception("Automation %s failed: %s", automation_id, exc)


# ---------------------------------------------------------------------------
# Temporal engine
# ---------------------------------------------------------------------------
class TemporalWorkflowEngine(WorkflowEngine):
    backend = "temporal"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._client: Any | None = None

    async def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            from temporalio.client import Client  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("temporalio is not installed") from exc
        self._client = await Client.connect(self.settings.TEMPORAL_TARGET)
        return self._client

    async def schedule(self, automation: Automation) -> str | None:  # pragma: no cover
        try:
            from temporalio.client import (  # type: ignore[import-not-found]
                Schedule,
                ScheduleActionStartWorkflow,
                ScheduleIntervalSpec,
                ScheduleSpec,
            )
        except ImportError:
            return None

        client = await self._get_client()
        spec_intervals = []
        if automation.interval_seconds:
            spec_intervals.append(
                ScheduleIntervalSpec(
                    every=__import__("datetime").timedelta(
                        seconds=automation.interval_seconds
                    )
                )
            )

        handle = await client.create_schedule(
            f"projectforge-automation-{automation.id}",
            Schedule(
                action=ScheduleActionStartWorkflow(
                    "RunAutomationWorkflow",
                    args=[automation.id],
                    id=f"automation-{automation.id}",
                    task_queue=self.settings.TEMPORAL_TASK_QUEUE,
                ),
                spec=ScheduleSpec(intervals=spec_intervals),
            ),
        )
        return getattr(handle, "id", None)

    async def cancel(self, automation: Automation) -> None:  # pragma: no cover
        if not automation.workflow_handle:
            return
        client = await self._get_client()
        try:
            handle = client.get_schedule_handle(automation.workflow_handle)
            await handle.delete()
        except Exception as exc:
            logger.warning("Could not delete Temporal schedule: %s", exc)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
_DEFAULT_ENGINE: WorkflowEngine | None = None


def get_workflow_engine() -> WorkflowEngine:
    global _DEFAULT_ENGINE
    if _DEFAULT_ENGINE is not None:
        return _DEFAULT_ENGINE

    settings = get_settings()
    backend = settings.WORKFLOW_BACKEND.lower()
    if backend == "temporal":
        _DEFAULT_ENGINE = TemporalWorkflowEngine(settings)
    else:
        _DEFAULT_ENGINE = InMemoryWorkflowEngine(
            poll_interval_seconds=settings.AUTOMATION_POLL_SECONDS
        )
    return _DEFAULT_ENGINE


def reset_workflow_engine() -> None:
    global _DEFAULT_ENGINE
    _DEFAULT_ENGINE = None
