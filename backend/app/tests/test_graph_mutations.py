import json
import tempfile
import unittest
import zipfile
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path

from automations.models import AutomationDefinition, AutomationSchedule, AutomationStatus, AutomationType
from automations.scheduling import apply_initial_schedule, compute_next_run_at, is_automation_due, reschedule_after_success
from automations.service import AutomationService
from automations.store import AutomationStore
from core.config import settings
from graph.adapter import InMemoryGraphStore
from graph.builder import ProjectGraphBuilder
from graph.models import NodeLabel
from graph.mutations import GraphMutationService
from ingestion.parsers.common.office import parse_office


class GraphMutationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        settings.INGESTION_MANIFEST_ROOT = str(Path(self.temp_dir.name) / "ingestion")
        InMemoryGraphStore._graphs.clear()
        manifest_dir = Path(settings.INGESTION_MANIFEST_ROOT) / "mutate"
        manifest_dir.mkdir(parents=True, exist_ok=True)
        manifest = {
            "project_id": "mutate",
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
        self.builder.build_from_latest_manifest("mutate")
        self.service = GraphMutationService(builder=self.builder)

    def tearDown(self):
        InMemoryGraphStore._graphs.clear()
        self.temp_dir.cleanup()

    def test_create_update_and_delete_task_node(self):
        created = self.service.create_node(
            "mutate",
            label=NodeLabel.TASK,
            properties={"name": "Finalize budget", "sequence": 1},
        )
        node_id = created["node"]["id"]

        updated = self.service.update_node(
            "mutate",
            node_id,
            properties={"name": "Finalize revised budget", "sequence": 2},
        )
        self.assertEqual(updated["node"]["properties"]["name"], "Finalize revised budget")

        deleted = self.service.delete_node("mutate", node_id)
        self.assertEqual(deleted["deleted_node_id"], node_id)
        graph = self.builder.get_graph("mutate")
        self.assertFalse(any(node["id"] == node_id for node in graph["graph"]["nodes"]))


class AutomationSchedulingTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        settings.AUTOMATION_WORKFLOW_ROOT = str(Path(self.temp_dir.name) / "automations")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_interval_schedule_sets_next_run_at(self):
        automation = AutomationDefinition(
            project_id="sched",
            type=AutomationType.TIMED_REMINDER,
            name="Hourly reminder",
            schedule=AutomationSchedule(interval_seconds=3600),
        )
        apply_initial_schedule(automation)
        self.assertIsNotNone(automation.next_run_at)

    async def test_recurring_automation_reschedules_after_success(self):
        service = AutomationService(store=AutomationStore())
        created = service.create(
            AutomationDefinition(
                project_id="sched",
                type=AutomationType.TIMED_REMINDER,
                name="Hourly reminder",
                schedule=AutomationSchedule(interval_seconds=60),
            )
        )
        automation_id = created["id"]
        result = await service.run("sched", automation_id)
        self.assertEqual(result["status"], AutomationStatus.SCHEDULED.value)
        stored = service.store.get("sched", automation_id)
        assert stored is not None
        self.assertIsNotNone(stored.next_run_at)

    async def test_list_due_includes_next_run_at(self):
        store = AutomationStore()
        automation = AutomationDefinition(
            project_id="due",
            type=AutomationType.TIMED_REMINDER,
            name="Due reminder",
            schedule=AutomationSchedule(run_at=(datetime.now(UTC) - timedelta(seconds=5)).isoformat()),
        )
        apply_initial_schedule(automation)
        store.upsert(automation)
        due = store.list_due()
        self.assertEqual(len(due), 1)
        self.assertTrue(is_automation_due(automation))


class OfficeTableParserTests(unittest.TestCase):
    def test_xlsx_parser_preserves_table_rows(self):
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr(
                "[Content_Types].xml",
                '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"></Types>',
            )
            archive.writestr(
                "xl/workbook.xml",
                (
                    '<?xml version="1.0"?>'
                    '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                    '<sheets><sheet name="Plan" sheetId="1" r:id="rId1"/></sheets></workbook>'
                ),
            )
            archive.writestr(
                "xl/_rels/workbook.xml.rels",
                (
                    '<?xml version="1.0"?>'
                    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
                    "</Relationships>"
                ),
            )
            archive.writestr(
                "xl/sharedStrings.xml",
                (
                    '<?xml version="1.0"?>'
                    '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                    "<si><t>Task</t></si><si><t>Owner</t></si><si><t>Budget review</t></si><si><t>PM</t></si>"
                    "</sst>"
                ),
            )
            archive.writestr(
                "xl/worksheets/sheet1.xml",
                (
                    '<?xml version="1.0"?>'
                    '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                    "<sheetData>"
                    '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c></row>'
                    '<row r="2"><c r="A2" t="s"><v>2</v></c><c r="B2" t="s"><v>3</v></c></row>'
                    "</sheetData></worksheet>"
                ),
            )

        parsed = parse_office(BytesIO(buffer.getvalue()), filename="plan.xlsx")
        self.assertEqual(parsed.metadata["table_count"], 1)
        self.assertIn("Sheet: Plan", parsed.chunks[0].text)
        self.assertIn("Task\tOwner", parsed.chunks[0].text)
        self.assertIn("Budget review\tPM", parsed.chunks[0].text)


if __name__ == "__main__":
    unittest.main()
