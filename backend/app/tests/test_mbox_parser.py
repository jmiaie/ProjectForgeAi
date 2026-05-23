import mailbox
import tempfile
import unittest
from email.message import EmailMessage
from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock, patch

from automations.temporal_activities import run_automation_activity, run_due_automations_activity
from automations.temporal_worker import temporal_worker_settings
from core.config import settings
from ingestion.parsers.common.mbox import parse_mbox


class MboxParserTests(unittest.TestCase):
    def _build_mbox(self, messages: list[EmailMessage]) -> bytes:
        with tempfile.TemporaryDirectory() as temp_dir:
            mbox_path = Path(temp_dir) / "archive.mbox"
            archive = mailbox.mbox(str(mbox_path))
            archive.lock()
            try:
                for message in messages:
                    archive.add(message)
                archive.flush()
            finally:
                archive.unlock()
                archive.close()
            return mbox_path.read_bytes()

    def test_mbox_parser_extracts_messages(self):
        first = EmailMessage()
        first["Subject"] = "Kickoff thread"
        first["From"] = "owner@example.com"
        first.set_content("Kickoff approved.")

        second = EmailMessage()
        second["Subject"] = "Schedule update"
        second["From"] = "pm@example.com"
        second.set_content("Schedule draft attached in follow-up.")

        parsed = parse_mbox(BytesIO(self._build_mbox([first, second])), filename="project.mbox")

        self.assertEqual(parsed.metadata["parser"], "mbox")
        self.assertEqual(parsed.metadata["message_count"], 2)
        self.assertEqual(parsed.metadata["chunk_count"], 2)
        self.assertIn("Kickoff approved", parsed.chunks[0].text)
        self.assertEqual(parsed.chunks[0].metadata["message_index"], 1)
        self.assertIn("Schedule draft attached", parsed.chunks[1].text)
        self.assertEqual(parsed.chunks[1].metadata["message_index"], 2)


class TemporalWorkerTests(unittest.IsolatedAsyncioTestCase):
    def test_temporal_worker_settings_include_dispatch_flag(self):
        payload = temporal_worker_settings()
        self.assertEqual(payload["task_queue"], settings.TEMPORAL_TASK_QUEUE)
        self.assertIn("use_worker_dispatch", payload)

    async def test_run_automation_activity_delegates_to_service(self):
        with patch("automations.service.AutomationService") as service_cls:
            service = service_cls.return_value
            service.run = AsyncMock(return_value={"status": "completed"})
            result = await run_automation_activity("proj_1", "auto_1", 2)
            service.run.assert_awaited_once_with("proj_1", "auto_1", attempt=2)
            self.assertEqual(result["status"], "completed")

    async def test_run_due_automations_activity_delegates_to_service(self):
        with patch("automations.service.AutomationService") as service_cls:
            service = service_cls.return_value
            service.run_due = AsyncMock(return_value={"processed": 1, "results": []})
            result = await run_due_automations_activity()
            service.run_due.assert_awaited_once_with()
            self.assertEqual(result["processed"], 1)


if __name__ == "__main__":
    unittest.main()
