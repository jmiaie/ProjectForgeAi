import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from core.config import settings
from graph.adapter import InMemoryGraphStore
from graph.builder import ProjectGraphBuilder
from graph.enricher import GraphEnrichmentService
from storage.locus_adapter import LocusAdapter


class GraphEnrichmentTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.original = {
            "INGESTION_MANIFEST_ROOT": settings.INGESTION_MANIFEST_ROOT,
            "LOCUS_STORE_ROOT": settings.LOCUS_STORE_ROOT,
        }
        settings.INGESTION_MANIFEST_ROOT = str(root / "ingestion")
        settings.LOCUS_STORE_ROOT = str(root / "locus")
        InMemoryGraphStore._graphs.clear()
        InMemoryLocusEngine_clear()

    def tearDown(self):
        for key, value in self.original.items():
            setattr(settings, key, value)
        InMemoryGraphStore._graphs.clear()
        InMemoryLocusEngine_clear()
        self.temp_dir.cleanup()

    async def test_enrichment_adds_fact_nodes_with_provenance(self):
        manifest_dir = Path(settings.INGESTION_MANIFEST_ROOT) / "enrich"
        manifest_dir.mkdir(parents=True, exist_ok=True)
        manifest = {
            "project_id": "enrich",
            "created_at": datetime.now(UTC).isoformat(),
            "files_processed": 1,
            "chunks_indexed": 1,
            "warnings": [],
            "documents": [
                {
                    "source": "plan.pdf",
                    "metadata": {"parser": "pdf", "source": "plan.pdf", "source_hash": "abc123", "chunk_count": 1},
                    "warnings": [],
                    "chunks": [{"parser": "pdf", "source_hash": "abc123", "chunk_index": 1}],
                }
            ],
            "storage": {},
            "session": {},
        }
        (manifest_dir / "latest.json").write_text(json.dumps(manifest))

        builder = ProjectGraphBuilder()
        builder.build_from_latest_manifest("enrich")

        locus = LocusAdapter("enrich")
        await locus.index_files(
            [
                {
                    "source": "plan.pdf",
                    "text": "From: owner@example.com\nKickoff milestone next week\nRisk: permit delay\nTask: finalize budget",
                    "metadata": {"parser": "pdf", "source_hash": "abc123", "chunk_index": 1, "source": "plan.pdf"},
                }
            ]
        )

        service = GraphEnrichmentService(builder=builder)
        result = await service.enrich("enrich")

        labels = {fact["label"] for fact in result["facts"]}
        self.assertIn("Stakeholder", labels)
        self.assertIn("Milestone", labels)
        self.assertIn("Risk", labels)
        self.assertIn("Task", labels)
        self.assertGreater(result["added_nodes"], 0)
        self.assertGreater(result["added_edges"], 0)

        graph = builder.get_graph("enrich")
        enriched = [node for node in graph["graph"]["nodes"] if node["label"] in {"Stakeholder", "Task", "Risk", "Milestone"}]
        self.assertTrue(enriched)
        derived = [edge for edge in graph["graph"]["edges"] if edge["type"] == "DERIVED_FROM"]
        self.assertTrue(derived)


def InMemoryLocusEngine_clear() -> None:
    from storage.locus_adapter import InMemoryLocusEngine

    InMemoryLocusEngine._stores.clear()


if __name__ == "__main__":
    unittest.main()
