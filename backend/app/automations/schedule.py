"""Schedule helpers: next-run computation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def compute_next_run(
    *,
    interval_seconds: int | None,
    cron: str | None,
    last_run_at: datetime | None,
    now: datetime | None = None,
) -> datetime | None:
    """Return the next-run timestamp.

    Cron support is left as a stub (returns ``None`` when only ``cron`` is
    supplied) — production deployments using Temporal will let Temporal own
    cron evaluation. Interval-based scheduling is fully implemented.
    """

    if interval_seconds is None and cron is None:
        return None
    if interval_seconds is None:
        return None  # cron-only: Temporal handles it; in-memory engine skips

    base = now or datetime.now(timezone.utc)
    if last_run_at is None:
        return base
    candidate = last_run_at + timedelta(seconds=interval_seconds)
    if candidate < base:
        return base
    return candidate
