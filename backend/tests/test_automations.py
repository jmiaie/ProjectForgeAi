"""Tests for the automation layer (kinds, schedule, runner, engine, API)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.automations.engine import (
    InMemoryWorkflowEngine,
    WorkflowEngine,
    get_workflow_engine,
    reset_workflow_engine,
)
from app.automations.kinds import AUTOMATION_KINDS, get_automation_kind
from app.automations.runner import AutomationRunner
from app.automations.schedule import compute_next_run
from app.db.repositories import (
    AuditLogRepository,
    AutomationRepository,
    ProjectRepository,
)
from app.db.session import get_session
from app.main import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
async def _ensure_project(project_id: str, name: str = "Auto Test") -> None:
    async with get_session() as session:
        repo = ProjectRepository(session)
        existing = await repo.get(project_id)
        if existing is None:
            await repo.create(
                project_id=project_id,
                name=name,
                compliance="standard",
                objective="Sprint 5 objective",
            )
        await session.commit()


# ---------------------------------------------------------------------------
# Schedule helpers
# ---------------------------------------------------------------------------
def test_compute_next_run_first_invocation_is_now() -> None:
    now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    nxt = compute_next_run(interval_seconds=3600, cron=None, last_run_at=None, now=now)
    assert nxt == now


def test_compute_next_run_advances_by_interval() -> None:
    now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    last = now - timedelta(seconds=120)
    nxt = compute_next_run(interval_seconds=300, cron=None, last_run_at=last, now=now)
    assert nxt == last + timedelta(seconds=300)


def test_compute_next_run_floors_to_now_when_overdue() -> None:
    now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    last = now - timedelta(days=30)
    nxt = compute_next_run(interval_seconds=3600, cron=None, last_run_at=last, now=now)
    assert nxt == now


def test_compute_next_run_returns_none_for_cron_only() -> None:
    assert compute_next_run(
        interval_seconds=None,
        cron="0 * * * *",
        last_run_at=None,
    ) is None


def test_get_automation_kind_known_and_unknown() -> None:
    assert get_automation_kind("status_report").specialist == "comms"
    with pytest.raises(ValueError):
        get_automation_kind("nope")


# ---------------------------------------------------------------------------
# Engine factory + memory engine basics
# ---------------------------------------------------------------------------
def test_engine_factory_defaults_to_memory() -> None:
    reset_workflow_engine()
    engine = get_workflow_engine()
    assert isinstance(engine, InMemoryWorkflowEngine)
    assert engine.backend == "memory"


@pytest.mark.asyncio
async def test_inmemory_engine_start_and_stop() -> None:
    engine = InMemoryWorkflowEngine(poll_interval_seconds=0.01)
    await engine.start()
    await asyncio.sleep(0.05)
    await engine.stop()
    assert engine._task is None


# ---------------------------------------------------------------------------
# API: catalogue + CRUD + run-now
# ---------------------------------------------------------------------------
def test_list_automation_kinds_endpoint() -> None:
    client = TestClient(app)
    res = client.get("/api/v1/automations/kinds")
    assert res.status_code == 200
    names = {kind["name"] for kind in res.json()["kinds"]}
    assert set(AUTOMATION_KINDS.keys()).issubset(names)


def test_create_list_run_cancel_automation_lifecycle() -> None:
    asyncio.run(_ensure_project("proj_auto_lc"))
    client = TestClient(app)

    res = client.post(
        "/api/v1/projects/proj_auto_lc/automations/",
        json={"kind": "status_report", "interval_seconds": 600, "max_runs": 2},
    )
    assert res.status_code == 200, res.text
    automation = res.json()
    automation_id = automation["id"]
    assert automation["status"] == "active"
    assert automation["interval_seconds"] == 600
    assert automation["next_run_at"] is not None

    res = client.get("/api/v1/projects/proj_auto_lc/automations/")
    assert res.status_code == 200
    items = res.json()["items"]
    assert any(a["id"] == automation_id for a in items)

    res = client.get(f"/api/v1/projects/proj_auto_lc/automations/{automation_id}")
    assert res.status_code == 200

    res = client.post(
        f"/api/v1/projects/proj_auto_lc/automations/{automation_id}/run-now"
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["automation_id"] == automation_id
    assert body["status"] in {"active", "completed"}
    assert "result" in body

    res = client.delete(f"/api/v1/projects/proj_auto_lc/automations/{automation_id}")
    assert res.status_code == 200
    assert res.json()["status"] == "cancelled"

    res = client.get(f"/api/v1/projects/proj_auto_lc/automations/{automation_id}")
    assert res.status_code == 200
    assert res.json()["status"] == "cancelled"


def test_create_automation_404_when_project_missing() -> None:
    client = TestClient(app)
    res = client.post(
        "/api/v1/projects/proj_missing/automations/",
        json={"kind": "status_report"},
    )
    assert res.status_code == 404


def test_create_automation_400_for_unknown_kind() -> None:
    asyncio.run(_ensure_project("proj_auto_kind"))
    client = TestClient(app)
    res = client.post(
        "/api/v1/projects/proj_auto_kind/automations/",
        json={"kind": "definitely-not-real"},
    )
    assert res.status_code == 400


def test_run_now_404_when_unknown_automation() -> None:
    asyncio.run(_ensure_project("proj_auto_run404"))
    client = TestClient(app)
    res = client.post(
        "/api/v1/projects/proj_auto_run404/automations/auto_unknown/run-now"
    )
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# Runner — exercises specialist + audit + max_runs completion
# ---------------------------------------------------------------------------
class _StubLLMRouter:
    async def call(self, req: Any) -> str:
        return "Risk: Vendor delay | Likelihood: medium | Impact: high | Mitigation: pre-contract penalty"


@pytest.mark.asyncio
async def test_runner_completes_after_max_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    project_id = "proj_runner_max"
    await _ensure_project(project_id, name="Runner Max")

    async with get_session() as session:
        repo = AutomationRepository(session)
        automation = await repo.create(
            kind="risk_reassessment",
            project_id=project_id,
            interval_seconds=300,
            max_runs=1,
            next_run_at=datetime.now(timezone.utc),
        )
        automation_id = automation.id
        await session.commit()

    # Patch the LLMRouter used by every specialist instance to a stub.
    from app.agents.specialists.base import SpecialistAgent

    original_init = SpecialistAgent.__init__

    def patched_init(self: SpecialistAgent, llm_router: Any = None) -> None:
        original_init(self, llm_router=_StubLLMRouter())

    monkeypatch.setattr(SpecialistAgent, "__init__", patched_init)

    runner = AutomationRunner()
    await runner.run(automation_id)

    async with get_session() as session:
        repo = AutomationRepository(session)
        refreshed = await repo.get(automation_id)
        assert refreshed is not None
        assert refreshed.runs_completed == 1
        assert refreshed.status == "completed"
        assert refreshed.next_run_at is None

        audit = AuditLogRepository(session)
        entries = await audit.list(
            project_id=project_id, action="automation.risk_reassessment.run"
        )
        assert entries, "runner should journal an audit entry per run"


@pytest.mark.asyncio
async def test_runner_skips_when_already_cancelled() -> None:
    project_id = "proj_runner_cancelled"
    await _ensure_project(project_id, name="Runner Cancelled")

    async with get_session() as session:
        repo = AutomationRepository(session)
        automation = await repo.create(
            kind="status_report",
            project_id=project_id,
            interval_seconds=600,
        )
        await repo.cancel(automation)
        await session.commit()
        automation_id = automation.id

    runner = AutomationRunner()
    result = await runner.run(automation_id)
    assert result["skipped"] is True
    assert result["status"] == "cancelled"


@pytest.mark.asyncio
async def test_repository_lists_due_rows() -> None:
    project_id = "proj_due"
    await _ensure_project(project_id, name="Due Test")

    past = datetime.now(timezone.utc) - timedelta(seconds=10)
    future = datetime.now(timezone.utc) + timedelta(seconds=600)

    async with get_session() as session:
        repo = AutomationRepository(session)
        due_one = await repo.create(
            kind="status_report",
            project_id=project_id,
            interval_seconds=300,
            next_run_at=past,
        )
        not_yet = await repo.create(
            kind="status_report",
            project_id=project_id,
            interval_seconds=300,
            next_run_at=future,
        )
        await session.commit()

        due = await repo.list_due(datetime.now(timezone.utc))
        ids = {row.id for row in due}
        assert due_one.id in ids
        assert not_yet.id not in ids
