"""Temporal workflow + activity definitions.

These are imported only when the Temporal worker bootstraps. The module
loads cleanly even when ``temporalio`` is not installed so static imports
elsewhere don't break.
"""

from __future__ import annotations

from typing import Any

try:
    from temporalio import activity, workflow  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - module degrades to no-op
    activity = None  # type: ignore[assignment]
    workflow = None  # type: ignore[assignment]


if activity is not None:

    @activity.defn  # type: ignore[misc]
    async def run_automation_activity(automation_id: str) -> dict[str, Any]:
        """Activity: execute one automation cycle via :class:`AutomationRunner`."""

        from app.automations.runner import AutomationRunner

        runner = AutomationRunner()
        return await runner.run(automation_id)


if workflow is not None:

    @workflow.defn(name="RunAutomationWorkflow")  # type: ignore[misc]
    class RunAutomationWorkflow:
        @workflow.run  # type: ignore[misc]
        async def run(self, automation_id: str) -> dict[str, Any]:
            from datetime import timedelta

            return await workflow.execute_activity(  # type: ignore[union-attr]
                run_automation_activity,
                automation_id,
                start_to_close_timeout=timedelta(minutes=10),
            )


__all__ = []
if activity is not None:
    __all__.append("run_automation_activity")
if workflow is not None:
    __all__.append("RunAutomationWorkflow")
