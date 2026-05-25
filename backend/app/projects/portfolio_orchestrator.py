import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from agents.orchestrator import OrchestratorAgent
from agents.state import OrchestratorRequest, OrchestratorStatus
from core.config import settings
from projects.registry import ProjectRegistry

PORTFOLIO_AGENTS = ["risk_analyst", "compliance_reviewer"]


class PortfolioProjectRun(BaseModel):
    project_id: str
    run_id: str
    status: str
    summary: str = ""
    warnings: list[str] = Field(default_factory=list)


class PortfolioRun(BaseModel):
    portfolio_run_id: str = Field(default_factory=lambda: f"portfolio_{uuid4().hex}")
    goal: str
    status: OrchestratorStatus = OrchestratorStatus.RUNNING
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    completed_at: str | None = None
    project_ids: list[str] = Field(default_factory=list)
    project_runs: list[PortfolioProjectRun] = Field(default_factory=list)
    artifacts: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)

    def complete(self) -> None:
        self.status = OrchestratorStatus.COMPLETED
        self.completed_at = datetime.now(UTC).isoformat()


class PortfolioRunStore:
    def __init__(self, root: str | None = None):
        self.root = Path(root or settings.ORCHESTRATION_RUN_ROOT) / "_portfolio"
        os.makedirs(self.root, exist_ok=True)

    def write(self, run: PortfolioRun) -> dict[str, Any]:
        path = self.root / f"{run.portfolio_run_id}.json"
        payload = run.model_dump(mode="json")
        path.write_text(json.dumps(payload, indent=2, sort_keys=True))
        latest = self.root / "latest.json"
        latest.write_text(json.dumps(payload, indent=2, sort_keys=True))
        return payload

    def read(self, portfolio_run_id: str | None = None) -> dict[str, Any] | None:
        path = self.root / f"{portfolio_run_id}.json" if portfolio_run_id else self.root / "latest.json"
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def list_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        runs = []
        for path in sorted(self.root.glob("portfolio_*.json"), reverse=True):
            runs.append(json.loads(path.read_text()))
        return runs[:limit]


class PortfolioOrchestratorService:
    def __init__(
        self,
        orchestrator: OrchestratorAgent | None = None,
        registry: ProjectRegistry | None = None,
        run_store: PortfolioRunStore | None = None,
    ):
        self.orchestrator = orchestrator or OrchestratorAgent()
        self.registry = registry or ProjectRegistry()
        self.run_store = run_store or PortfolioRunStore()

    async def run(
        self,
        *,
        goal: str,
        project_ids: list[str] | None = None,
        requested_agents: list[str] | None = None,
    ) -> dict[str, Any]:
        agents = requested_agents or PORTFOLIO_AGENTS
        targets = project_ids or [
            project.project_id
            for project in self.registry.list_projects(include_archived=False)
        ]
        if not targets:
            raise ValueError("No active projects available for portfolio orchestrator run")

        portfolio_run = PortfolioRun(goal=goal, project_ids=targets)
        compliance_findings: list[dict[str, Any]] = []
        risk_findings: list[dict[str, Any]] = []

        for project_id in targets:
            if self.registry.get(project_id) is None:
                portfolio_run.warnings.append(f"Skipped unknown project: {project_id}")
                continue

            result = await self.orchestrator.run(
                OrchestratorRequest(
                    project_id=project_id,
                    goal=goal,
                    requested_agents=agents,
                )
            )
            steps = result.get("steps", [])
            summary = "; ".join(step.get("summary", "") for step in steps if step.get("summary")) or goal
            project_run = PortfolioProjectRun(
                project_id=project_id,
                run_id=result.get("run_id", ""),
                status=result.get("status", OrchestratorStatus.COMPLETED.value),
                summary=summary[:240],
                warnings=result.get("warnings", []),
            )
            portfolio_run.project_runs.append(project_run)
            portfolio_run.warnings.extend(result.get("warnings", []))

            for step in steps:
                output = step.get("output", {})
                if step.get("name") == "compliance_reviewer":
                    compliance_findings.append(
                        {"project_id": project_id, "summary": step.get("summary", ""), "output": output}
                    )
                if step.get("name") == "risk_analyst":
                    risk_findings.append(
                        {"project_id": project_id, "summary": step.get("summary", ""), "output": output}
                    )

        portfolio_run.artifacts = {
            "compliance_findings": compliance_findings,
            "risk_findings": risk_findings,
            "projects_scanned": len(portfolio_run.project_runs),
        }
        portfolio_run.complete()
        return self.run_store.write(portfolio_run)

    def list_runs(self, limit: int = 20) -> dict[str, Any]:
        return {"runs": self.run_store.list_runs(limit)}

    def get_run(self, portfolio_run_id: str) -> dict[str, Any]:
        payload = self.run_store.read(portfolio_run_id)
        if payload is None:
            raise ValueError(f"Unknown portfolio run: {portfolio_run_id}")
        return payload
