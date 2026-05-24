from datetime import UTC, datetime, timedelta

from automations.models import AutomationDefinition, AutomationSchedule, AutomationStatus


def compute_next_run_at(
    schedule: AutomationSchedule,
    *,
    reference: datetime | None = None,
) -> datetime | None:
    now = reference or datetime.now(UTC)

    if schedule.run_at:
        run_at = datetime.fromisoformat(schedule.run_at)
        if run_at.tzinfo is None:
            run_at = run_at.replace(tzinfo=UTC)
        return run_at

    if schedule.cron:
        try:
            from croniter import croniter
        except ImportError as exc:
            raise ValueError("croniter is required for cron schedules") from exc
        base = now.astimezone(UTC).replace(tzinfo=None)
        iterator = croniter(schedule.cron, base)
        next_run = iterator.get_next(datetime)
        return next_run.replace(tzinfo=UTC)

    if schedule.interval_seconds and schedule.interval_seconds > 0:
        return now + timedelta(seconds=schedule.interval_seconds)

    return None


def apply_initial_schedule(automation: AutomationDefinition) -> None:
    next_run = compute_next_run_at(automation.schedule)
    if next_run is not None:
        automation.next_run_at = next_run.isoformat()


def reschedule_after_success(automation: AutomationDefinition) -> None:
    schedule = automation.schedule
    if schedule.interval_seconds and schedule.interval_seconds > 0:
        automation.status = AutomationStatus.SCHEDULED
        automation.next_run_at = (
            datetime.now(UTC) + timedelta(seconds=schedule.interval_seconds)
        ).isoformat()
        return

    if schedule.cron:
        next_run = compute_next_run_at(schedule, reference=datetime.now(UTC))
        if next_run is not None:
            automation.status = AutomationStatus.SCHEDULED
            automation.next_run_at = next_run.isoformat()
            return

    automation.status = AutomationStatus.COMPLETED
    automation.next_run_at = None


def is_automation_due(automation: AutomationDefinition, *, now: datetime | None = None) -> bool:
    current = now or datetime.now(UTC)

    if automation.next_retry_at:
        retry_at = datetime.fromisoformat(automation.next_retry_at)
        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=UTC)
        if retry_at <= current:
            return True

    if automation.next_run_at:
        run_at = datetime.fromisoformat(automation.next_run_at)
        if run_at.tzinfo is None:
            run_at = run_at.replace(tzinfo=UTC)
        if run_at <= current:
            return True

    return False
