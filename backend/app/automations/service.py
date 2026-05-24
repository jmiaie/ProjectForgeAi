from datetime import UTC, datetime, timedelta
from typing import Any

from agents.orchestrator import OrchestratorAgent
from agents.state import OrchestratorRequest
from automations.models import (
    AutomationDefinition,
    AutomationRunResult,
    AutomationStatus,
    AutomationType,
)
from automations.scheduling import apply_initial_schedule, reschedule_after_success
from automations.store import AutomationStore
from compliance.enforcer import ComplianceEnforcer
from core.config import settings
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
        if automation.max_retries <= 0:
            automation.max_retries = settings.AUTOMATION_MAX_RETRIES
        if automation.requires_approval or automation.type == AutomationType.APPROVAL_GATE:
            automation.status = AutomationStatus.WAITING_APPROVAL
            automation.requires_approval = True
        else:
            apply_initial_schedule(automation)
        payload = self.store.upsert(automation)
        return payload

    async def sync_temporal_schedule(self, project_id: str, automation_id: str) -> dict:
        from automations.temporal_schedules import sync_automation_schedule

        automation = self._get_required(project_id, automation_id)
        try:
            return await sync_automation_schedule(automation)
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    def list(self, project_id: str) -> dict:
        return {"project_id": project_id, "automations": self.store.list(project_id)}

    def runs(self, project_id: str, limit: int = 100) -> dict:
        return {"project_id": project_id, "runs": self.store.list_runs(project_id, limit)}

    def dead_letters(self, project_id: str, limit: int = 100) -> dict:
        return {"project_id": project_id, "dead_letters": self.store.list_dead_letters(project_id, limit)}

    def approve(self, project_id: str, automation_id: str, approved_by: str) -> dict:
        automation = self._get_required(project_id, automation_id)
        automation.approved_by = approved_by
        automation.requires_approval = False
        automation.status = AutomationStatus.SCHEDULED
        automation.touch()
        return self.store.upsert(automation)

    async def retry(self, project_id: str, automation_id: str) -> dict:
        automation = self._get_required(project_id, automation_id)
        automation.retry_count = 0
        automation.next_retry_at = None
        automation.status = AutomationStatus.SCHEDULED
        automation.touch()
        self.store.upsert(automation)
        return await self.run(project_id, automation_id, attempt=1)

    async def run(self, project_id: str, automation_id: str, attempt: int = 1) -> dict:
        automation = self._get_required(project_id, automation_id)
        max_retries = automation.max_retries or settings.AUTOMATION_MAX_RETRIES

        if automation.requires_approval:
            result = AutomationRunResult(
                automation_id=automation.id,
                project_id=project_id,
                status=AutomationStatus.WAITING_APPROVAL,
                action="approval_required",
                attempt=attempt,
                warnings=[f"{automation.name} requires approval before execution"],
            )
            return self.store.append_run(result)

        automation.status = AutomationStatus.RUNNING
        automation.retry_count = attempt
        automation.touch()
        self.store.upsert(automation)

        try:
            output = await self._execute(automation)
            automation.last_run_at = datetime.now(UTC).isoformat()
            automation.run_count += 1
            automation.retry_count = 0
            automation.next_retry_at = None
            reschedule_after_success(automation)
            automation.touch()
            self.store.upsert(automation)
            if settings.TEMPORAL_SYNC_SCHEDULES and automation.next_run_at:
                try:
                    from automations.temporal_schedules import sync_automation_schedule

                    await sync_automation_schedule(automation)
                except Exception:
                    pass
            result = AutomationRunResult(
                automation_id=automation.id,
                project_id=project_id,
                status=automation.status,
                action=automation.type.value,
                attempt=attempt,
                output=output,
            )
            return self.store.append_run(result)
        except Exception as exc:
            return self._handle_failure(automation, attempt=attempt, max_retries=max_retries, error=str(exc))

    async def run_due(self) -> dict[str, Any]:
        due = self.store.list_due()
        results = []
        for automation in due:
            attempt = automation.retry_count + 1 if automation.next_retry_at else 1
            result = await self.run(
                automation.project_id,
                automation.id,
                attempt=attempt,
            )
            results.append(result)
        return {"processed": len(results), "results": results}

    def _handle_failure(
        self,
        automation: AutomationDefinition,
        *,
        attempt: int,
        max_retries: int,
        error: str,
    ) -> dict:
        if attempt < max_retries:
            backoff = settings.AUTOMATION_RETRY_BACKOFF_SECONDS * attempt
            automation.status = AutomationStatus.SCHEDULED
            automation.next_retry_at = (datetime.now(UTC) + timedelta(seconds=backoff)).isoformat()
            automation.touch()
            self.store.upsert(automation)
            result = AutomationRunResult(
                automation_id=automation.id,
                project_id=automation.project_id,
                status=AutomationStatus.FAILED,
                action=automation.type.value,
                attempt=attempt,
                retriable=True,
                error=error,
                warnings=[error, f"Retry scheduled at {automation.next_retry_at}"],
            )
            return self.store.append_run(result)

        automation.status = AutomationStatus.DEAD_LETTER
        automation.next_retry_at = None
        automation.touch()
        self.store.upsert(automation)
        result = AutomationRunResult(
            automation_id=automation.id,
            project_id=automation.project_id,
            status=AutomationStatus.DEAD_LETTER,
            action=automation.type.value,
            attempt=attempt,
            retriable=False,
            error=error,
            warnings=[error, "Automation moved to dead letter queue"],
        )
        self.store.append_dead_letter(result)
        return self.store.append_run(result)

    async def _execute(self, automation: AutomationDefinition) -> dict[str, Any]:
        if automation.payload.get("force_fail"):
            raise RuntimeError(automation.payload.get("error_message", "Forced automation failure"))

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
