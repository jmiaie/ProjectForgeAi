from typing import Any

from automations.models import AutomationDefinition
from core.config import settings


def schedule_id_for(automation: AutomationDefinition) -> str:
    return f"projectforge-{automation.project_id}-{automation.id}"


def _has_temporal_schedule(automation: AutomationDefinition) -> bool:
    schedule = automation.schedule
    return bool(schedule.interval_seconds or schedule.cron or schedule.run_at)


async def sync_automation_schedule(automation: AutomationDefinition) -> dict[str, Any]:
    if not settings.TEMPORAL_SYNC_SCHEDULES or not _has_temporal_schedule(automation):
        return {"status": "skipped", "reason": "temporal schedule sync disabled or no schedule"}

    from automations.temporal_worker import connect_temporal_client
    from temporalio.client import (
        Schedule,
        ScheduleActionStartWorkflow,
        ScheduleAlreadyRunningError,
        ScheduleIntervalSpec,
        ScheduleSpec,
        ScheduleUpdate,
    )

    from automations.temporal_workflows import RunAutomationWorkflow

    client = await connect_temporal_client()
    schedule_id = schedule_id_for(automation)
    spec = _build_schedule_spec(automation)
    action = ScheduleActionStartWorkflow(
        RunAutomationWorkflow.run,
        args=[automation.project_id, automation.id, 1],
        id=f"scheduled-{automation.id}-",
        task_queue=settings.TEMPORAL_TASK_QUEUE,
    )
    schedule = Schedule(action=action, spec=spec)

    try:
        handle = await client.create_schedule(schedule_id, schedule)
        return {"status": "created", "schedule_id": handle.id}
    except ScheduleAlreadyRunningError:
        handle = client.get_schedule_handle(schedule_id)
        await handle.update(lambda _: ScheduleUpdate(schedule=schedule))
        return {"status": "updated", "schedule_id": schedule_id}


async def delete_automation_schedule(automation: AutomationDefinition) -> dict[str, Any]:
    if not settings.TEMPORAL_SYNC_SCHEDULES:
        return {"status": "skipped", "reason": "temporal schedule sync disabled"}

    from automations.temporal_worker import connect_temporal_client

    client = await connect_temporal_client()
    schedule_id = schedule_id_for(automation)
    handle = client.get_schedule_handle(schedule_id)
    await handle.delete()
    return {"status": "deleted", "schedule_id": schedule_id}


def _build_schedule_spec(automation: AutomationDefinition) -> Any:
    from datetime import timedelta

    from temporalio.client import ScheduleCalendarSpec, ScheduleIntervalSpec, ScheduleSpec

    schedule = automation.schedule
    if schedule.cron:
        return ScheduleSpec(cron_expressions=[schedule.cron], time_zone_name=schedule.timezone)

    if schedule.interval_seconds and schedule.interval_seconds > 0:
        return ScheduleSpec(
            intervals=[ScheduleIntervalSpec(every=timedelta(seconds=schedule.interval_seconds))],
            time_zone_name=schedule.timezone,
        )

    if schedule.run_at:
        run_at = schedule.run_at
        if "T" in run_at:
            date_part, time_part = run_at.split("T", 1)
            year, month, day = [int(part) for part in date_part.split("-")]
            hour, minute, second = (time_part.split(":") + ["00"])[:3]
            return ScheduleSpec(
                calendars=[
                    ScheduleCalendarSpec(
                        year=[year],
                        month=[month],
                        day_of_month=[day],
                        hour=[int(hour)],
                        minute=[int(minute)],
                        second=[int(float(second))],
                    )
                ],
                time_zone_name=schedule.timezone,
            )

    return ScheduleSpec(intervals=[ScheduleIntervalSpec(every=timedelta(hours=24))])
