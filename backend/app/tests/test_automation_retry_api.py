import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

import main
from automations.models import AutomationDefinition, AutomationStatus, AutomationType
from automations.store import AutomationStore
from core.config import settings


class AutomationRetryApiTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original = {"AUTOMATION_WORKFLOW_ROOT": settings.AUTOMATION_WORKFLOW_ROOT}
        settings.AUTOMATION_WORKFLOW_ROOT = str(Path(self.temp_dir.name) / "automations")
        self.client = TestClient(main.app)

    def tearDown(self):
        for key, value in self.original.items():
            setattr(settings, key, value)
        self.temp_dir.cleanup()

    async def test_dead_letter_and_retry_endpoints(self):
        created = self.client.post(
            "/api/v1/projects/api-dlq/automations",
            json={
                "type": AutomationType.TIMED_REMINDER.value,
                "name": "API failing reminder",
                "payload": {"force_fail": True},
                "max_retries": 1,
            },
        )
        self.assertEqual(created.status_code, 200)
        automation_id = created.json()["id"]

        failed = self.client.post(f"/api/v1/projects/api-dlq/automations/{automation_id}/run")
        self.assertEqual(failed.status_code, 200)
        self.assertEqual(failed.json()["status"], AutomationStatus.DEAD_LETTER.value)

        dead_letters = self.client.get("/api/v1/projects/api-dlq/automations/dead-letters")
        self.assertEqual(dead_letters.status_code, 200)
        self.assertEqual(len(dead_letters.json()["dead_letters"]), 1)

        store = AutomationStore()
        automation = store.get("api-dlq", automation_id)
        assert automation is not None
        automation.payload = {"message": "Recovered via API"}
        store.upsert(automation)

        retry = self.client.post(f"/api/v1/projects/api-dlq/automations/{automation_id}/retry")
        self.assertEqual(retry.status_code, 200)
        self.assertEqual(retry.json()["status"], AutomationStatus.COMPLETED.value)

    async def test_temporal_run_due_endpoint(self):
        created = self.client.post(
            "/api/v1/projects/api-due/automations",
            json={
                "type": AutomationType.TIMED_REMINDER.value,
                "name": "Due reminder",
                "payload": {"message": "Run due"},
            },
        )
        automation_id = created.json()["id"]

        store = AutomationStore()
        automation = store.get("api-due", automation_id)
        assert automation is not None
        automation.status = AutomationStatus.SCHEDULED
        automation.retry_count = 0
        automation.next_retry_at = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
        store.upsert(automation)

        response = self.client.post("/api/v1/automations/temporal/run-due")
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(response.json()["processed"], 1)


if __name__ == "__main__":
    unittest.main()
