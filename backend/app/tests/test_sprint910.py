import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from agents.audit import OrchestratorAuditStore
from agents.orchestrator import OrchestratorAgent
from agents.run_store import OrchestratorRunStore
from agents.state import OrchestratorRequest
from core.config import settings
from core.integrations_manager import IntegrationsManager
from integrations.connectors.oauth import oauth_credentials_configured, require_oauth_credentials
from integrations.connectors.webhook import WebhookConnector
from integrations.registry import ConnectorRegistry


class Sprint910Tests(unittest.IsolatedAsyncioTestCase):
    def test_webhook_connector_registers_events(self):
        import asyncio

        connector = WebhookConnector()
        payload = asyncio.run(
            connector.authenticate(
                {
                    "webhook_url": "https://hooks.example.com/projectforge",
                    "events": ["project.updated"],
                }
            )
        )
        self.assertEqual(payload["events"], ["project.updated"])
        self.assertTrue(payload["secret"])

    def test_registry_includes_webhook_connector(self):
        config = ConnectorRegistry.get_config("webhook")
        self.assertEqual(config["type"], "webhook")
        connector = ConnectorRegistry.get_connector("webhook")
        self.assertIsInstance(connector, WebhookConnector)

    async def test_register_webhook_via_manager(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings.INTEGRATIONS_CONNECTION_ROOT = temp_dir
            settings.COMPLIANCE_PROFILE_ROOT = str(Path(temp_dir) / "profiles")
            settings.COMPLIANCE_AUDIT_ROOT = str(Path(temp_dir) / "audit")
            settings.ENCRYPTION_KEY = "test-key"
            manager = IntegrationsManager()
            result = await manager.register_webhook(
                "wh-proj",
                {"webhook_url": "https://hooks.example.com/pf", "events": ["automation.completed"]},
            )
            self.assertEqual(result["status"], "connected")
            self.assertNotIn("secret", result["connection"]["summary"])

    def test_oauth_credentials_gate_when_mock_disabled(self):
        with patch.object(settings, "OAUTH_MOCK_TOKEN_EXCHANGE", False):
            with patch.object(settings, "GOOGLE_OAUTH_CLIENT_ID", None):
                with patch.object(settings, "GOOGLE_OAUTH_CLIENT_SECRET", None):
                    self.assertFalse(oauth_credentials_configured("google"))
                    with self.assertRaises(ValueError):
                        require_oauth_credentials("google")

    async def test_oauth_real_exchange_uses_http_client(self):
        from integrations.connectors.oauth import OAuthConnector

        connector = OAuthConnector("google", {"provider": "google", "scopes": ["email"]})
        mock_response = unittest.mock.Mock()
        mock_response.json.return_value = {
            "access_token": "real-token",
            "token_type": "Bearer",
            "expires_in": 3600,
        }
        mock_response.raise_for_status = unittest.mock.Mock()

        with patch.object(settings, "OAUTH_MOCK_TOKEN_EXCHANGE", False), patch.object(
            settings, "GOOGLE_OAUTH_CLIENT_ID", "client-id"
        ), patch.object(settings, "GOOGLE_OAUTH_CLIENT_SECRET", "client-secret"), patch.object(
            settings, "OAUTH_ALLOW_UNVERIFIED_STATE", True
        ), patch(
            "integrations.connectors.oauth.httpx.AsyncClient"
        ) as client_cls:
            client = AsyncMock()
            client.__aenter__.return_value = client
            client.post = AsyncMock(return_value=mock_response)
            client_cls.return_value = client
            token = await connector.authenticate({"code": "exchange-code-123", "state": None})
        self.assertEqual(token["access_token"], "real-token")

    async def test_mcp_sse_discovery_uses_sdk(self):
        from integrations.connectors.mcp import MCPConnector

        connector = MCPConnector()
        with patch(
            "integrations.connectors.mcp.mcp_transport.discover_tools_via_sse",
            new=AsyncMock(return_value=[{"name": "search"}]),
        ) as discover:
            tools = await connector._discover_tools(
                transport="sse",
                server_url="https://mcp.example.com/sse",
            )
        discover.assert_awaited_once()
        self.assertEqual(tools[0]["name"], "search")

    async def test_orchestrator_writes_audit_events(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = OrchestratorRunStore(root=str(root / "runs"))
            audit = OrchestratorAuditStore(root=str(root / "runs"))
            agent = OrchestratorAgent(
                run_store=store,
                audit_store=audit,
                tool_context_factory=lambda project_id: _FakeToolContext(project_id),
            )
            await agent.run(
                OrchestratorRequest(project_id="audit-proj", goal="Audit test", run_id="run_audit")
            )
            events = audit.list_events("audit-proj", "run_audit")
            event_types = [event["event_type"] for event in events]
            self.assertIn("run_started", event_types)
            self.assertIn("run_completed", event_types)
            self.assertIn("step_completed", event_types)


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
