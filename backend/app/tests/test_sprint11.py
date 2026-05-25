import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agents.orchestrator import OrchestratorAgent
from agents.run_store import OrchestratorRunStore
from compliance.enforcer import ComplianceEnforcer
from core.config import settings
from core.rbac import RBACService
from core.upgrade_manager import UpgradeManager
from fastapi.testclient import TestClient

import main


class Sprint11Tests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        settings.RBAC_MEMBERSHIP_ROOT = str(root / "rbac")
        settings.COMPLIANCE_PROFILE_ROOT = str(root / "compliance")
        settings.COMPLIANCE_AUDIT_ROOT = str(root / "audit")
        settings.ORCHESTRATION_RUN_ROOT = str(root / "orchestrator")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_rbac_blocks_viewer_from_graph_write_when_enforced(self):
        rbac = RBACService()
        actor = rbac.resolve_actor("viewer-user", "viewer")
        with patch.object(settings, "RBAC_ENFORCE", True):
            decision = rbac.check("proj", actor, "graph.write")
        self.assertFalse(decision.allowed)

    def test_rbac_owner_can_manage_access_when_enforced(self):
        rbac = RBACService()
        actor = rbac.resolve_actor("owner-user", "owner")
        with patch.object(settings, "RBAC_ENFORCE", True):
            decision = rbac.check("proj", actor, "access.manage")
        self.assertTrue(decision.allowed)

    def test_assign_member_persists_role(self):
        rbac = RBACService()
        rbac.assign_member("proj", "alice", "editor")
        role = rbac.store.get_role("proj", "alice")
        self.assertEqual(role, "editor")

    def test_upgrade_blocks_self_learning_on_starter_tier(self):
        upgrade = UpgradeManager()
        with patch.object(settings, "PROJECT_TIER", "starter"):
            decision = upgrade.check_feature("proj", "self_learning")
        self.assertFalse(decision.allowed)

    def test_upgrade_allows_self_learning_on_enterprise_tier(self):
        compliance = ComplianceEnforcer()
        compliance.set_profile("proj", "standard")
        upgrade = UpgradeManager(compliance=compliance)
        with patch.object(settings, "PROJECT_TIER", "enterprise"):
            decision = upgrade.check_feature("proj", "self_learning")
        self.assertTrue(decision.allowed)

    def test_compliance_blocks_self_learning_for_hipaa(self):
        compliance = ComplianceEnforcer()
        compliance.set_profile("proj", "hipaa")
        upgrade = UpgradeManager(compliance=compliance)
        with patch.object(settings, "PROJECT_TIER", "enterprise"):
            decision = upgrade.check_feature("proj", "self_learning")
        self.assertFalse(decision.allowed)

    async def test_self_improve_endpoint_runs_orchestrator(self):
        store = OrchestratorRunStore(root=str(Path(self.temp_dir.name) / "runs"))
        agent = OrchestratorAgent(
            run_store=store,
            tool_context_factory=lambda project_id: _FakeToolContext(project_id),
        )
        main.app.dependency_overrides[main.get_orchestrator_agent] = lambda: agent
        try:
            with patch.object(settings, "PROJECT_TIER", "enterprise"):
                client = TestClient(main.app)
                response = client.post(
                    "/api/v1/projects/self-proj/upgrade/self-improve",
                    json={"goal": "Improve risk register"},
                )
            self.assertEqual(response.status_code, 200)
            self.assertIn("self_improvement", response.json())
        finally:
            main.app.dependency_overrides.clear()

    def test_access_members_api(self):
        client = TestClient(main.app)
        assign = client.post(
            "/api/v1/projects/access-proj/access/members",
            json={"actor_id": "bob", "role": "editor"},
            headers={"X-ProjectForge-Actor": "owner", "X-ProjectForge-Role": "owner"},
        )
        self.assertEqual(assign.status_code, 200)
        listed = client.get("/api/v1/projects/access-proj/access/members")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()["members"]), 1)


class _FakeToolContext:
    def __init__(self, project_id: str):
        self.project_id = project_id

    async def graph_snapshot(self):
        return {"node_count": 0, "edge_count": 0, "warnings": [], "graph": {"nodes": [], "edges": []}}

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
