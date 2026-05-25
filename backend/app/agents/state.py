from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class OrchestratorStatus(StrEnum):
    PLANNED = "planned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentStep(BaseModel):
    name: str
    status: OrchestratorStatus = OrchestratorStatus.PLANNED
    summary: str = ""
    output: dict[str, Any] = Field(default_factory=dict)


class OrchestratorRequest(BaseModel):
    project_id: str
    goal: str = "Prepare project operating plan"
    run_id: str | None = None
    resume: bool = False
    requested_agents: list[str] = Field(default_factory=list)


class OrchestratorRun(BaseModel):
    run_id: str = Field(default_factory=lambda: f"run_{uuid4().hex}")
    project_id: str
    goal: str
    status: OrchestratorStatus = OrchestratorStatus.RUNNING
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    completed_at: str | None = None
    steps: list[AgentStep] = Field(default_factory=list)
    artifacts: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)

    def complete(self) -> None:
        self.status = OrchestratorStatus.COMPLETED
        self.completed_at = datetime.now(UTC).isoformat()
