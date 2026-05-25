import json
import tempfile
import unittest
import zipfile
from datetime import UTC, datetime
from email.message import EmailMessage
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from automations.models import AutomationDefinition, AutomationSchedule, AutomationType
from automations.temporal_schedules import schedule_id_for
from core.config import settings
from graph.adapter import InMemoryGraphStore
from graph.bootstrap import MIGRATIONS, SCHEMA_VERSION
from graph.builder import ProjectGraphBuilder
from graph.models import EdgeType, NodeLabel
from graph.mutations import GraphMutationService
from ingestion.parsers.common.email import parse_email
from ingestion.parsers.common.office import parse_office


class GraphEdgeMutationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        settings.INGESTION_MANIFEST_ROOT = str(Path(self.temp_dir.name) / "ingestion")
        InMemoryGraphStore._graphs.clear()
        manifest_dir = Path(settings.INGESTION_MANIFEST_ROOT) / "edges"
        manifest_dir.mkdir(parents=True, exist_ok=True)
        manifest = {
            "project_id": "edges",
            "created_at": datetime.now(UTC).isoformat(),
            "files_processed": 1,
            "chunks_indexed": 1,
            "warnings": [],
            "documents": [
                {
                    "source": "plan.pdf",
                    "metadata": {"parser": "pdf", "source_hash": "abc", "chunk_count": 1},
                    "warnings": [],
                    "chunks": [{"parser": "pdf", "source_hash": "abc", "chunk_index": 1}],
                }
            ],
            "storage": {},
            "session": {},
        }
        (manifest_dir / "latest.json").write_text(json.dumps(manifest))
        self.builder = ProjectGraphBuilder()
        self.builder.build_from_latest_manifest("edges")
        self.service = GraphMutationService(builder=self.builder)

    def tearDown(self):
        InMemoryGraphStore._graphs.clear()
        self.temp_dir.cleanup()

    def test_create_and_delete_dependency_edge(self):
        task_a = self.service.create_node(
            "edges",
            label=NodeLabel.TASK,
            properties={"name": "Design review", "sequence": 1},
        )
        task_b = self.service.create_node(
            "edges",
            label=NodeLabel.TASK,
            properties={"name": "Implementation", "sequence": 2},
        )
        created = self.service.create_edge(
            "edges",
            source_id=task_b["node"]["id"],
            target_id=task_a["node"]["id"],
            edge_type=EdgeType.DEPENDS_ON,
        )
        self.assertEqual(created["edge"]["type"], EdgeType.DEPENDS_ON.value)

        deleted = self.service.delete_edge(
            "edges",
            source_id=task_b["node"]["id"],
            target_id=task_a["node"]["id"],
            edge_type=EdgeType.DEPENDS_ON,
        )
        self.assertEqual(deleted["deleted_edge"]["type"], EdgeType.DEPENDS_ON.value)


class EmailAttachmentTests(unittest.TestCase):
    def test_email_parser_indexes_docx_attachment_chunks(self):
        docx_buffer = BytesIO()
        with zipfile.ZipFile(docx_buffer, "w") as archive:
            archive.writestr(
                "word/document.xml",
                (
                    '<?xml version="1.0" encoding="UTF-8"?>'
                    '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                    "<w:body><w:p><w:r><w:t>Attachment scope approved</w:t></w:r></w:p></w:body>"
                    "</w:document>"
                ),
            )

        attachment = EmailMessage()
        attachment.set_payload(docx_buffer.getvalue())
        attachment.add_header("Content-Disposition", "attachment", filename="scope.docx")
        attachment.add_header("Content-Type", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

        message = EmailMessage()
        message["Subject"] = "Project files"
        message.set_content("See attached scope.")
        message.make_mixed()
        message.attach(attachment)

        parsed = parse_email(BytesIO(message.as_bytes()), filename="files.eml")
        self.assertGreaterEqual(parsed.metadata["attachment_count"], 1)
        self.assertGreater(parsed.metadata["attachment_chunks_indexed"], 0)
        self.assertTrue(any("Attachment scope approved" in chunk.text for chunk in parsed.chunks))


class OfficeStructureTests(unittest.TestCase):
    def test_docx_parser_extracts_heading_and_table(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            docx_path = Path(temp_dir) / "plan.docx"
            with zipfile.ZipFile(docx_path, "w") as archive:
                archive.writestr(
                    "word/document.xml",
                    (
                        '<?xml version="1.0" encoding="UTF-8"?>'
                        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                        "<w:body>"
                        '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Project Plan</w:t></w:r></w:p>'
                        "<w:tbl><w:tr><w:tc><w:p><w:r><w:t>Task</w:t></w:r></w:p></w:tc>"
                        "<w:tc><w:p><w:r><w:t>Owner</w:t></w:r></w:p></w:tc></w:tr>"
                        "<w:tr><w:tc><w:p><w:r><w:t>Budget</w:t></w:r></w:p></w:tc>"
                        "<w:tc><w:p><w:r><w:t>PM</w:t></w:r></w:p></w:tc></w:tr></w:tbl>"
                        "</w:body></w:document>"
                    ),
                )

            parsed = parse_office(docx_path)
            self.assertIn("Heading: Project Plan", parsed.chunks[0].text)
            self.assertIn("Task\tOwner", parsed.chunks[0].text)


class Neo4jBootstrapTests(unittest.TestCase):
    def test_bootstrap_statements_defined(self):
        self.assertGreater(SCHEMA_VERSION, 0)
        self.assertTrue(MIGRATIONS)

    def test_adapter_bootstrap_skips_without_driver(self):
        from graph.adapter import Neo4jGraphAdapter

        adapter = Neo4jGraphAdapter()
        adapter._driver = None
        result = adapter.bootstrap()
        self.assertEqual(result["status"], "skipped")


class TemporalScheduleHelperTests(unittest.IsolatedAsyncioTestCase):
    def test_schedule_id_is_stable(self):
        automation = AutomationDefinition(
            project_id="proj",
            type=AutomationType.TIMED_REMINDER,
            name="Reminder",
            schedule=AutomationSchedule(interval_seconds=3600),
        )
        self.assertEqual(schedule_id_for(automation), f"projectforge-proj-{automation.id}")

    async def test_sync_skips_when_disabled(self):
        from automations.temporal_schedules import sync_automation_schedule

        automation = AutomationDefinition(
            project_id="proj",
            type=AutomationType.TIMED_REMINDER,
            name="Reminder",
            schedule=AutomationSchedule(interval_seconds=3600),
        )
        with patch.object(settings, "TEMPORAL_SYNC_SCHEDULES", False):
            result = await sync_automation_schedule(automation)
        self.assertEqual(result["status"], "skipped")


if __name__ == "__main__":
    unittest.main()
