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
        "status": "configured",
    }


async def run_due_automations(service: AutomationService | None = None) -> dict[str, Any]:
    runner = service or AutomationService()
    result = await runner.run_due()
    return {
        **temporal_worker_settings(),
        **result,
    }
