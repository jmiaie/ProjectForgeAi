from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class AutomationType(StrEnum):
    TIMED_REMINDER = "timed_reminder"
    RECURRING_REPORT = "recurring_report"
    INTEGRATION_SYNC = "integration_sync"
    APPROVAL_GATE = "approval_gate"


class AutomationStatus(StrEnum):
    SCHEDULED = "scheduled"
    WAITING_APPROVAL = "waiting_approval"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"
    CANCELLED = "cancelled"


class AutomationSchedule(BaseModel):
    run_at: str | None = None
    interval_seconds: int | None = None
    cron: str | None = None
    timezone: str = "UTC"


class AutomationDefinition(BaseModel):
    id: str = Field(default_factory=lambda: f"auto_{uuid4().hex}")
    project_id: str
    type: AutomationType
    name: str
    payload: dict[str, Any] = Field(default_factory=dict)
    schedule: AutomationSchedule = Field(default_factory=AutomationSchedule)
    status: AutomationStatus = AutomationStatus.SCHEDULED
    requires_approval: bool = False
    approved_by: str | None = None
    max_retries: int = 3
    retry_count: int = 0
    next_retry_at: str | None = None
    next_run_at: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    last_run_at: str | None = None
    run_count: int = 0

    def touch(self) -> None:
        self.updated_at = datetime.now(UTC).isoformat()


class AutomationRunResult(BaseModel):
    automation_id: str
    project_id: str
    status: AutomationStatus
    action: str
    attempt: int = 1
    retriable: bool = False
    error: str | None = None
    output: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
