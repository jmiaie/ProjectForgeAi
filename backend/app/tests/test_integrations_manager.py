import tempfile
import unittest
from pathlib import Path

from compliance.audit import ComplianceAuditStore
from compliance.enforcer import ComplianceEnforcer, ComplianceProfileStore
from core.integrations_manager import IntegrationsManager
from integrations.connection_store import ConnectionStore


class IntegrationsManagerTests(unittest.IsolatedAsyncioTestCase):
    async def test_oauth_start_and_connect_stores_encrypted_secret(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = ConnectionStore(root=str(root / "connections"), encryption_key="test-key")
            manager = IntegrationsManager(connection_store=store)

            start = await manager.start_oauth("google", project_id="int-test")
            self.assertIn("authorization_url", start)
            self.assertEqual(start["connector"], "google")

            result = await manager.connect("google", {"code": "abc123"}, project_id="int-test")
            self.assertEqual(result["status"], "connected")
            self.assertNotIn("access_token", result["connection"]["summary"])

            secret = store.load_secret("int-test", "google")
            self.assertEqual(secret["access_token"], "placeholder_access_abc123")

            health = await manager.health_check("int-test", "google")
            self.assertEqual(health["status"], "connected")
            self.assertTrue(health["checks"]["token_present"])

    async def test_api_key_connection_is_persisted_without_exposing_key(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = ConnectionStore(root=str(Path(temp_dir) / "connections"), encryption_key="test-key")
            manager = IntegrationsManager(connection_store=store)

            result = await manager.connect("jira", {"api_key": "secret", "base_url": "https://jira.local"}, "api-test")

            self.assertEqual(result["status"], "connected")
            self.assertNotIn("api_key", result["connection"]["summary"])
            self.assertEqual(store.load_secret("api-test", "jira")["api_key"], "secret")

    async def test_restricted_profile_blocks_connection_write(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            compliance = ComplianceEnforcer(
                profile_store=ComplianceProfileStore(root=str(root / "profiles")),
                audit_store=ComplianceAuditStore(root=str(root / "audit")),
            )
            compliance.set_profile("restricted", "hipaa")
            manager = IntegrationsManager(
                compliance=compliance,
                connection_store=ConnectionStore(root=str(root / "connections"), encryption_key="test-key"),
            )

            with self.assertRaises(PermissionError):
                await manager.connect("google", {"code": "abc"}, project_id="restricted")

    async def test_mcp_discovery_uses_stored_tools(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = ConnectionStore(root=str(Path(temp_dir) / "connections"), encryption_key="test-key")
            manager = IntegrationsManager(connection_store=store)
            store.upsert(
                project_id="mcp-test",
                connector_type="mcp_server",
                connection={
                    "id": "mcp_server",
                    "server_url": "https://mcp.local",
                    "tools": [{"name": "search_docs"}],
                },
            )

            tools = await manager.discover_mcp_tools("mcp-test")

            self.assertEqual(tools["tool_count"], 1)
            self.assertEqual(tools["tools"][0]["name"], "search_docs")


if __name__ == "__main__":
    unittest.main()
