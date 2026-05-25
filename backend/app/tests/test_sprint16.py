import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from auth.oidc_provider import OIDCProvider
from auth.session import AuthSessionStore
from compliance.soc2_export import SOC2ExportService
from compliance.enforcer import ComplianceEnforcer
from core.config import settings
from core.rbac import RBACService
from fastapi.testclient import TestClient

import main


class Sprint16Tests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        settings.AUTH_SESSION_ROOT = str(root / "auth")
        settings.RBAC_MEMBERSHIP_ROOT = str(root / "rbac")
        settings.COMPLIANCE_PROFILE_ROOT = str(root / "compliance")
        settings.COMPLIANCE_AUDIT_ROOT = str(root / "audit")
        settings.ORCHESTRATION_RUN_ROOT = str(root / "orchestrator")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_mock_login_creates_session(self):
        with patch.object(settings, "OIDC_ENABLED", True), patch.object(settings, "OIDC_MOCK", True):
            client = TestClient(main.app)
            response = client.post(
                "/api/v1/auth/mock-login",
                json={"actor_id": "alice", "email": "alice@example.com", "role": "admin"},
            )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["actor_id"], "alice")
        self.assertIn("token", payload)

    def test_bearer_session_resolves_actor_context(self):
        store = AuthSessionStore()
        session = store.create(actor_id="sso-user", email="sso@example.com", role="admin")
        client = TestClient(main.app)
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {session['token']}"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["actor_id"], "sso-user")

    def test_oidc_group_role_map(self):
        provider = OIDCProvider()
        with patch.object(settings, "OIDC_GROUP_ROLE_MAP", '{"admins":"admin","editors":"editor"}'):
            role = provider.resolve_role(["editors"])
        self.assertEqual(role, "editor")

    def test_soc2_export_includes_controls(self):
        compliance = ComplianceEnforcer()
        compliance.set_profile("proj-soc2", "soc2")
        rbac = RBACService()
        rbac.assign_member("proj-soc2", "owner-user", "owner")
        exporter = SOC2ExportService(compliance=compliance, rbac=rbac)
        export = exporter.export_project("proj-soc2")
        self.assertEqual(export["project_id"], "proj-soc2")
        self.assertEqual(len(export["controls"]), 6)
        self.assertIn("summary", export)

    def test_soc2_export_endpoint(self):
        client = TestClient(main.app)
        response = client.get("/api/v1/projects/proj-soc2-api/compliance/export/soc2")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["framework"], "SOC 2 Type II (starter mapping)")
        self.assertTrue(payload["controls"])

    def test_auth_status_endpoint(self):
        with patch.object(settings, "OIDC_ENABLED", True):
            client = TestClient(main.app)
            response = client.get("/api/v1/auth/status")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["enabled"])


if __name__ == "__main__":
    unittest.main()
