import tempfile
import unittest
from pathlib import Path

from graph.builder import ProjectGraphBuilder
from graph.models import EdgeType, NodeLabel
from ingestion.manifest import IngestionManifestStore
from ingestion.parsers.base import ParsedChunk, ParsedDocument


class FakeGraphAdapter:
    def __init__(self):
        self.graph = None

    def upsert_graph(self, graph):
        self.graph = graph
        return {"backend": "fake", "native": False, "node_count": graph.node_count, "edge_count": graph.edge_count}

    def rebuild_graph(self, graph):
        self.graph = graph
        return {
            "backend": "fake",
            "native": False,
            "node_count": graph.node_count,
            "edge_count": graph.edge_count,
            "orphans_removed": 0,
        }

    def get_graph(self, project_id):
        return self.graph if self.graph and self.graph.project_id == project_id else None

    def status(self):
        return {"backend": "fake", "native": False}


class ProjectGraphBuilderTests(unittest.TestCase):
    def test_build_graph_from_ingestion_manifest(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_store = IngestionManifestStore(root=str(Path(temp_dir) / "manifests"))
            document = ParsedDocument(
                source="scope.pdf",
                chunks=[
                    ParsedChunk(
                        source="scope.pdf",
                        text="Scope baseline",
                        metadata={
                            "parser": "pdf",
                            "source_hash": "abc123",
                            "page": 1,
                            "chunk_index": 1,
                            "chunk_size": 14,
                        },
                    )
                ],
                metadata={
                    "parser": "pdf",
                    "source": "scope.pdf",
                    "source_hash": "abc123",
                    "chunk_count": 1,
                },
                warnings=[],
            )
            manifest_store.write(
                project_id="graph-test",
                documents=[document],
                storage={"native_ready": False},
                session={"status": "started"},
            )

            adapter = FakeGraphAdapter()
            builder = ProjectGraphBuilder(adapter=adapter, manifest_store=manifest_store)
            result = builder.build_from_latest_manifest("graph-test")

            self.assertEqual(result["node_count"], 3)
            self.assertEqual(result["edge_count"], 2)
            labels = {node.label for node in adapter.graph.nodes}
            self.assertEqual(labels, {NodeLabel.PROJECT, NodeLabel.DOCUMENT, NodeLabel.CHUNK})
            edge_types = {edge.type for edge in adapter.graph.edges}
            self.assertEqual(edge_types, {EdgeType.HAS_DOCUMENT, EdgeType.HAS_CHUNK})

    def test_missing_manifest_creates_empty_project_graph(self):
        adapter = FakeGraphAdapter()
        builder = ProjectGraphBuilder(
            adapter=adapter,
            manifest_store=IngestionManifestStore(root="/tmp/projectforge-missing-manifest-test"),
        )

        result = builder.build_from_latest_manifest("missing")

        self.assertEqual(result["node_count"], 1)
        self.assertEqual(result["edge_count"], 0)
        self.assertIn("missing: no ingestion manifest found", result["warnings"])


if __name__ == "__main__":
    unittest.main()
