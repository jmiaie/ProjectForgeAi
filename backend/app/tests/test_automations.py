import tempfile
import unittest
from pathlib import Path

from agents.orchestrator import OrchestratorAgent
from agents.run_store import OrchestratorRunStore
from automations.models import AutomationDefinition, AutomationType
from automations.service import AutomationService
from automations.store import AutomationStore
from compliance.audit import ComplianceAuditStore
from compliance.enforcer import ComplianceEnforcer, ComplianceProfileStore
from core.integrations_manager import IntegrationsManager
from integrations.connection_store import ConnectionStore


class AutomationServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_timed_reminder_runs_locally(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            service = AutomationService(store=AutomationStore(root=str(Path(temp_dir) / "automations")))
            created = service.create(
                AutomationDefinition(
                    project_id="auto-test",
                    type=AutomationType.TIMED_REMINDER,
                    name="Owner reminder",
                    payload={"message": "Review schedule", "recipient": "owner@example.com"},
                )
            )

            result = await service.run("auto-test", created["id"])

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["output"]["message"], "Review schedule")
            self.assertEqual(service.list("auto-test")["automations"][0]["run_count"], 1)

    async def test_approval_gate_waits_until_approved(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            service = AutomationService(store=AutomationStore(root=str(Path(temp_dir) / "automations")))
            created = service.create(
                AutomationDefinition(
                    project_id="approval-test",
                    type=AutomationType.APPROVAL_GATE,
                    name="Human gate",
                    payload={"message": "Release report"},
                )
            )

            blocked = await service.run("approval-test", created["id"])
            self.assertEqual(blocked["status"], "waiting_approval")

            approved = service.approve("approval-test", created["id"], "pm@example.com")
            self.assertEqual(approved["status"], "scheduled")

            result = await service.run("approval-test", created["id"])
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["output"]["approved_by"], "pm@example.com")

    async def test_recurring_report_runs_orchestrator_subset(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            service = AutomationService(
                store=AutomationStore(root=str(root / "automations")),
                orchestrator=OrchestratorAgent(
                    run_store=OrchestratorRunStore(root=str(root / "runs")),
                    tool_context_factory=lambda project_id: _FakeToolContext(project_id),
                ),
            )
            created = service.create(
                AutomationDefinition(
                    project_id="report-test",
                    type=AutomationType.RECURRING_REPORT,
                    name="Weekly report",
                    payload={"goal": "Generate weekly status", "report_type": "weekly"},
                )
            )

            result = await service.run("report-test", created["id"])

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["output"]["report_type"], "weekly")
            self.assertEqual(result["output"]["status"], "completed")

    async def test_restricted_integration_sync_fails_without_approval(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            compliance = ComplianceEnforcer(
                profile_store=ComplianceProfileStore(root=str(root / "profiles")),
                audit_store=ComplianceAuditStore(root=str(root / "audit")),
            )
            compliance.set_profile("sync-test", "hipaa")
            service = AutomationService(
                store=AutomationStore(root=str(root / "automations")),
                integrations=IntegrationsManager(
                    compliance=compliance,
                    connection_store=ConnectionStore(root=str(root / "connections"), encryption_key="test-key"),
                ),
                compliance=compliance,
            )
            created = service.create(
                AutomationDefinition(
                    project_id="sync-test",
                    type=AutomationType.INTEGRATION_SYNC,
                    name="Sync Google",
                    payload={"connector_type": "google"},
                )
            )

            result = await service.run("sync-test", created["id"])

            self.assertEqual(result["status"], "failed")
            self.assertTrue(result["warnings"])


class _FakeToolContext:
    def __init__(self, project_id: str):
        self.project_id = project_id

    async def graph_snapshot(self):
        return {"node_count": 1, "edge_count": 0, "warnings": [], "graph": {"nodes": [], "edges": []}}

    async def retrieve_context(self, query: str, limit: int = 5):
        return []

    async def recommended_integrations(self):
        return []

    async def record_decision(self, message: str):
        return None

    def storage_status(self):
        return {"graph": {"backend": "memory"}}

    def compliance_profile(self):
        return {"project_id": self.project_id, "category": "standard"}


if __name__ == "__main__":
    unittest.main()
