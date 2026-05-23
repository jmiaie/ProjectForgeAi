import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from automations.models import AutomationDefinition, AutomationStatus, AutomationType
from automations.service import AutomationService
from automations.store import AutomationStore


class AutomationRetryTests(unittest.IsolatedAsyncioTestCase):
    async def test_failed_automation_retries_then_dead_letters(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            service = AutomationService(store=AutomationStore(root=str(Path(temp_dir) / "automations")))
            created = service.create(
                AutomationDefinition(
                    project_id="dlq-test",
                    type=AutomationType.TIMED_REMINDER,
                    name="Failing reminder",
                    max_retries=2,
                    payload={"force_fail": True, "error_message": "boom"},
                )
            )

            first = await service.run("dlq-test", created["id"], attempt=1)
            self.assertEqual(first["status"], AutomationStatus.FAILED.value)
            self.assertTrue(first["retriable"])

            second = await service.run("dlq-test", created["id"], attempt=2)
            self.assertEqual(second["status"], AutomationStatus.DEAD_LETTER.value)
            self.assertEqual(len(service.dead_letters("dlq-test")["dead_letters"]), 1)
            automation = service.store.get("dlq-test", created["id"])
            assert automation is not None
            self.assertEqual(automation.status, AutomationStatus.DEAD_LETTER)

    async def test_retry_from_dead_letter_resets_and_runs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            service = AutomationService(store=AutomationStore(root=str(Path(temp_dir) / "automations")))
            created = service.create(
                AutomationDefinition(
                    project_id="retry-test",
                    type=AutomationType.TIMED_REMINDER,
                    name="Recoverable reminder",
                    max_retries=1,
                    payload={"force_fail": True},
                )
            )
            await service.run("retry-test", created["id"], attempt=1)
            automation = service.store.get("retry-test", created["id"])
            assert automation is not None
            automation.payload = {"message": "Recovered"}
            service.store.upsert(automation)

            result = await service.retry("retry-test", created["id"])
            self.assertEqual(result["status"], AutomationStatus.COMPLETED.value)

    async def test_run_due_processes_scheduled_retries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            service = AutomationService(store=AutomationStore(root=str(Path(temp_dir) / "automations")))
            created = service.create(
                AutomationDefinition(
                    project_id="due-test",
                    type=AutomationType.TIMED_REMINDER,
                    name="Due reminder",
                    max_retries=2,
                    payload={"message": "Due now"},
                )
            )
            automation = service.store.get("due-test", created["id"])
            assert automation is not None
            automation.status = AutomationStatus.SCHEDULED
            automation.retry_count = 1
            automation.next_retry_at = (datetime.now(UTC) - timedelta(seconds=5)).isoformat()
            service.store.upsert(automation)

            result = await service.run_due()
            self.assertEqual(result["processed"], 1)
            self.assertEqual(result["results"][0]["status"], AutomationStatus.COMPLETED.value)


if __name__ == "__main__":
    unittest.main()
