import asyncio
import logging

from automations.temporal_activities import run_automation_activity, run_due_automations_activity
from automations.temporal_workflows import DueAutomationsWorkflow, RunAutomationWorkflow
from automations.temporal_worker import connect_temporal_client, temporal_worker_settings
from core.config import settings

logger = logging.getLogger(__name__)


async def run_worker() -> None:
    from temporalio.worker import Worker

    client = await connect_temporal_client()
    worker = Worker(
        client,
        task_queue=settings.TEMPORAL_TASK_QUEUE,
        workflows=[RunAutomationWorkflow, DueAutomationsWorkflow],
        activities=[run_automation_activity, run_due_automations_activity],
    )
    info = temporal_worker_settings()
    logger.info(
        "Starting Temporal worker on %s namespace=%s task_queue=%s",
        info["address"],
        info["namespace"],
        info["task_queue"],
    )
    await worker.run()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
