from typing import Any

from temporalio import activity


@activity.defn(name="run_automation")
async def run_automation_activity(project_id: str, automation_id: str, attempt: int = 1) -> dict[str, Any]:
    from automations.service import AutomationService

    service = AutomationService()
    return await service.run(project_id, automation_id, attempt=attempt)


@activity.defn(name="run_due_automations")
async def run_due_automations_activity() -> dict[str, Any]:
    from automations.service import AutomationService

    service = AutomationService()
    return await service.run_due()
