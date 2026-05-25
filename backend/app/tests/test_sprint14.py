import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from core.config import settings
from core.llm_keys import LLMKeyStore
from core.llm_router import LLMRequest, LLMRouter
from core.llm_routing import select_model
from core.usage_meter import LLMUsageMeter
from fastapi.testclient import TestClient

import main


class Sprint14Tests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        settings.LLM_KEY_ROOT = str(root / "keys")
        settings.LLM_USAGE_ROOT = str(root / "usage")
        settings.ENCRYPTION_KEY = "test-key"
        settings.PROJECT_REGISTRY_ROOT = str(root / "projects")
        settings.COMPLIANCE_PROFILE_ROOT = str(root / "compliance")
        settings.COMPLIANCE_AUDIT_ROOT = str(root / "audit")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_starter_reasoning_offers_upsell(self):
        routing = select_model(
            project_id="proj_starter",
            requested_model=None,
            task_type="reasoning",
            use_flagship=False,
            compliance_required_model=None,
        )
        with patch("core.llm_routing.project_tier", return_value="starter"):
            routing = select_model(
                project_id="proj_starter",
                requested_model=None,
                task_type="reasoning",
                use_flagship=False,
                compliance_required_model=None,
            )
        self.assertEqual(routing.routing_tier, "economy")
        self.assertTrue(routing.upsell_available)

    def test_pro_reasoning_routes_flagship(self):
        with patch("core.llm_routing.project_tier", return_value="pro"):
            routing = select_model(
                project_id="proj_pro",
                requested_model=None,
                task_type="reasoning",
                use_flagship=False,
                compliance_required_model=None,
            )
        self.assertEqual(routing.routing_tier, "flagship")
        self.assertEqual(routing.model, settings.FLAGSHIP_LLM_MODEL)

    def test_llm_key_store_encrypts_and_lists(self):
        store = LLMKeyStore()
        store.upsert(project_id="p1", provider="openai", api_key="sk-test-key")
        keys = store.list_keys("p1")
        self.assertEqual(len(keys), 1)
        self.assertNotIn("api_key", keys[0])
        secret = store.get_secret("p1", "openai")
        self.assertEqual(secret, "sk-test-key")

    def test_usage_meter_records_events(self):
        meter = LLMUsageMeter()
        meter.record(
            project_id="p1",
            model="groq/llama",
            task_type="general",
            prompt_tokens=10,
            completion_tokens=20,
            routing_tier="economy",
        )
        summary = meter.summary("p1")
        self.assertEqual(summary["call_count"], 1)
        self.assertEqual(summary["total_tokens"], 30)

    async def _test_router_records_usage(self):
        router = LLMRouter()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content='{"facts":[]}'))]
        mock_response.usage = MagicMock(prompt_tokens=5, completion_tokens=7)

        with patch("litellm.acompletion", new=AsyncMock(return_value=mock_response)):
            with patch("core.llm_routing.project_tier", return_value="starter"):
                result = await router.call_with_metadata(
                    LLMRequest(
                        project_id="meter-proj",
                        task_type="general",
                        messages=[{"role": "user", "content": "hello"}],
                    )
                )
        self.assertEqual(result.routing_tier, "economy")
        summary = router.usage_meter.summary("meter-proj")
        self.assertEqual(summary["call_count"], 1)

    def test_router_records_usage_sync(self):
        import asyncio

        asyncio.run(self._test_router_records_usage())

    def test_llm_keys_api(self):
        client = TestClient(main.app)
        save = client.post(
            "/api/v1/projects/proj_123/llm/keys",
            json={"provider": "groq", "api_key": "gsk_test"},
        )
        self.assertEqual(save.status_code, 200)
        listed = client.get("/api/v1/projects/proj_123/llm/keys")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()["keys"]), 1)

    def test_llm_routing_api(self):
        client = TestClient(main.app)
        response = client.get("/api/v1/projects/proj_123/llm/routing")
        self.assertEqual(response.status_code, 200)
        self.assertIn("flagship_model", response.json())


if __name__ == "__main__":
    unittest.main()
