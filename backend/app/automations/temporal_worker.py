from typing import Any

from automations.service import AutomationService
from core.config import settings


async def connect_temporal_client():
    from temporalio.client import Client

    return await Client.connect(
        settings.TEMPORAL_ADDRESS,
        namespace=settings.TEMPORAL_NAMESPACE,
    )


def temporal_worker_settings() -> dict:
    return {
        "address": settings.TEMPORAL_ADDRESS,
        "namespace": settings.TEMPORAL_NAMESPACE,
        "task_queue": settings.TEMPORAL_TASK_QUEUE,
        "use_worker_dispatch": settings.TEMPORAL_USE_WORKER_DISPATCH,
        "status": "configured",
    }


async def start_run_automation_workflow(
    project_id: str,
    automation_id: str,
    *,
    attempt: int = 1,
) -> dict[str, Any]:
    from automations.temporal_workflows import RunAutomationWorkflow

    client = await connect_temporal_client()
    handle = await client.start_workflow(
        RunAutomationWorkflow.run,
        args=[project_id, automation_id, attempt],
        id=f"automation-{project_id}-{automation_id}-{attempt}",
        task_queue=settings.TEMPORAL_TASK_QUEUE,
    )
    return {
        **temporal_worker_settings(),
        "workflow_id": handle.id,
        "run_id": handle.result_run_id,
        "status": "started",
    }


async def start_due_automations_workflow() -> dict[str, Any]:
    from automations.temporal_workflows import DueAutomationsWorkflow

    client = await connect_temporal_client()
    handle = await client.start_workflow(
        DueAutomationsWorkflow.run,
        id=f"due-automations-{handle_id_suffix()}",
        task_queue=settings.TEMPORAL_TASK_QUEUE,
    )
    return {
        **temporal_worker_settings(),
        "workflow_id": handle.id,
        "run_id": handle.result_run_id,
        "status": "started",
    }


def handle_id_suffix() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")


async def run_due_automations(service: AutomationService | None = None) -> dict[str, Any]:
    if settings.TEMPORAL_USE_WORKER_DISPATCH:
        try:
            return await start_due_automations_workflow()
        except Exception as exc:
            runner = service or AutomationService()
            result = await runner.run_due()
            return {
                **temporal_worker_settings(),
                **result,
                "dispatch": "local_fallback",
                "dispatch_error": str(exc),
            }

    runner = service or AutomationService()
    result = await runner.run_due()
    return {
        **temporal_worker_settings(),
        **result,
        "dispatch": "local",
    }
