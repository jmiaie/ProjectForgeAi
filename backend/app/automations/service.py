from datetime import UTC, datetime
from typing import Any

from agents.orchestrator import OrchestratorAgent
from agents.state import OrchestratorRequest
from automations.models import (
    AutomationDefinition,
    AutomationRunResult,
    AutomationStatus,
    AutomationType,
)
from automations.store import AutomationStore
from compliance.enforcer import ComplianceEnforcer
from core.integrations_manager import IntegrationsManager


class AutomationService:
    def __init__(
        self,
        store: AutomationStore | None = None,
        orchestrator: OrchestratorAgent | None = None,
        integrations: IntegrationsManager | None = None,
        compliance: ComplianceEnforcer | None = None,
    ):
        self.store = store or AutomationStore()
        self.orchestrator = orchestrator or OrchestratorAgent()
        self.integrations = integrations or IntegrationsManager()
        self.compliance = compliance or ComplianceEnforcer()

    def create(self, automation: AutomationDefinition) -> dict:
        if automation.requires_approval or automation.type == AutomationType.APPROVAL_GATE:
            automation.status = AutomationStatus.WAITING_APPROVAL
            automation.requires_approval = True
        return self.store.upsert(automation)

    def list(self, project_id: str) -> dict:
        return {"project_id": project_id, "automations": self.store.list(project_id)}

    def runs(self, project_id: str, limit: int = 100) -> dict:
        return {"project_id": project_id, "runs": self.store.list_runs(project_id, limit)}

    def approve(self, project_id: str, automation_id: str, approved_by: str) -> dict:
        automation = self._get_required(project_id, automation_id)
        automation.approved_by = approved_by
        automation.requires_approval = False
        automation.status = AutomationStatus.SCHEDULED
        automation.touch()
        return self.store.upsert(automation)

    async def run(self, project_id: str, automation_id: str) -> dict:
        automation = self._get_required(project_id, automation_id)
        if automation.requires_approval:
            result = AutomationRunResult(
                automation_id=automation.id,
                project_id=project_id,
                status=AutomationStatus.WAITING_APPROVAL,
                action="approval_required",
                warnings=[f"{automation.name} requires approval before execution"],
            )
            return self.store.append_run(result)

        automation.status = AutomationStatus.RUNNING
        automation.touch()
        self.store.upsert(automation)

        try:
            output = await self._execute(automation)
            automation.status = AutomationStatus.COMPLETED
            automation.last_run_at = datetime.now(UTC).isoformat()
            automation.run_count += 1
            automation.touch()
            self.store.upsert(automation)
            result = AutomationRunResult(
                automation_id=automation.id,
                project_id=project_id,
                status=AutomationStatus.COMPLETED,
                action=automation.type.value,
                output=output,
            )
        except Exception as exc:
            automation.status = AutomationStatus.FAILED
            automation.touch()
            self.store.upsert(automation)
            result = AutomationRunResult(
                automation_id=automation.id,
                project_id=project_id,
                status=AutomationStatus.FAILED,
                action=automation.type.value,
                warnings=[str(exc)],
            )
        return self.store.append_run(result)

    async def _execute(self, automation: AutomationDefinition) -> dict[str, Any]:
        if automation.type == AutomationType.TIMED_REMINDER:
            return {
                "message": automation.payload.get("message", "Project reminder"),
                "recipient": automation.payload.get("recipient", "project_owner"),
                "delivery": "queued_local",
            }

        if automation.type == AutomationType.RECURRING_REPORT:
            goal = automation.payload.get("goal", "Generate recurring project status report")
            run = await self.orchestrator.run(
                OrchestratorRequest(
                    project_id=automation.project_id,
                    goal=goal,
                    requested_agents=["intake_analyst", "risk_analyst", "template_generator"],
                )
            )
            return {
                "report_type": automation.payload.get("report_type", "weekly_status"),
                "orchestrator_run_id": run["run_id"],
                "status": run["status"],
            }

        if automation.type == AutomationType.INTEGRATION_SYNC:
            connector = automation.payload.get("connector_type", "mcp_server")
            decision = self.compliance.check_action(
                automation.project_id,
                "external_write",
                payload={"connector_type": connector, "automation_id": automation.id},
            )
            if not decision.allowed:
                raise PermissionError(decision.reason)
            health = await self.integrations.health_check(automation.project_id, connector)
            return {"connector": connector, "health": health, "sync": "queued_local"}

        if automation.type == AutomationType.APPROVAL_GATE:
            return {
                "approved_by": automation.approved_by,
                "message": automation.payload.get("message", "Approval gate released"),
            }

        raise ValueError(f"Unsupported automation type: {automation.type}")

    def _get_required(self, project_id: str, automation_id: str) -> AutomationDefinition:
        automation = self.store.get(project_id, automation_id)
        if automation is None:
            raise ValueError(f"Automation {automation_id} not found for {project_id}")
        return automation
