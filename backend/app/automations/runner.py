"""Executes a single automation run.

Independent of any workflow engine — :class:`TemporalWorkflowEngine` and
:class:`InMemoryWorkflowEngine` both drive this runner so behaviour stays
identical regardless of where the schedule lives.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.agents.specialists import DEFAULT_SPECIALISTS
from app.agents.state import OrchestratorState, empty_state
from app.automations.kinds import get_automation_kind
from app.automations.schedule import compute_next_run
from app.db.models import Automation
from app.db.repositories import AuditLogRepository, AutomationRepository
from app.db.session import get_session
from app.graph.builder import GraphBuilder


class AutomationRunner:
    """Executes one automation cycle and updates persistence."""

    async def run(self, automation_id: str) -> dict[str, Any]:
        async with get_session() as session:
            repo = AutomationRepository(session)
            automation = await repo.get(automation_id)
            if automation is None:
                raise ValueError(f"Automation {automation_id} not found")
            if automation.status != "active":
                return {
                    "automation_id": automation.id,
                    "status": automation.status,
                    "skipped": True,
                }

            result = await self._execute(automation)

            now = datetime.now(timezone.utc)
            next_run = compute_next_run(
                interval_seconds=automation.interval_seconds,
                cron=automation.cron,
                last_run_at=now,
                now=now,
            )
            await repo.update_after_run(
                automation, last_run_at=now, next_run_at=next_run
            )

            audit = AuditLogRepository(session)
            await audit.record(
                action=get_automation_kind(automation.kind).audit_action,
                project_id=automation.project_id,
                payload={
                    "automation_id": automation.id,
                    "runs_completed": automation.runs_completed,
                    "summary": result.get("summary"),
                    "artefacts": len(result.get("artefacts", [])),
                },
            )
            await session.commit()

            return {
                "automation_id": automation.id,
                "ran_at": now.isoformat(),
                "next_run_at": automation.next_run_at.isoformat()
                if automation.next_run_at
                else None,
                "status": automation.status,
                "result": result,
            }

    async def _execute(self, automation: Automation) -> dict[str, Any]:
        kind = get_automation_kind(automation.kind)
        specialist_name = automation.config.get("specialist") or kind.specialist

        specialist_cls = DEFAULT_SPECIALISTS.get(specialist_name)
        if specialist_cls is None:
            return {
                "summary": f"Unknown specialist '{specialist_name}'",
                "artefacts": [],
                "warnings": [f"unknown_specialist:{specialist_name}"],
            }

        agent = specialist_cls()
        state: OrchestratorState = empty_state(
            automation.project_id or "unknown",
            automation.config.get("objective") or kind.description,
        )
        state["compliance_category"] = automation.config.get(
            "compliance_category", "standard"
        )
        output = await agent.run(state)

        if automation.project_id:
            try:
                builder = GraphBuilder(automation.project_id)
                await builder.add_orchestrator_outputs({specialist_name: output})
            except Exception as exc:  # pragma: no cover - defensive
                output.setdefault("warnings", []).append(f"graph_update_failed:{exc}")

        return dict(output)
