from typing import Any

from graph.adapter import Neo4jGraphAdapter
from graph.ids import make_node_id as _node_id
from graph.models import EdgeType, GraphEdge, GraphNode, NodeLabel, ProjectGraph
from ingestion.manifest import IngestionManifestStore


class ProjectGraphBuilder:
    def __init__(
        self,
        adapter: Neo4jGraphAdapter | None = None,
        manifest_store: IngestionManifestStore | None = None,
    ):
        self.adapter = adapter or Neo4jGraphAdapter()
        self.manifest_store = manifest_store or IngestionManifestStore()

    def build_from_latest_manifest(self, project_id: str) -> dict[str, Any]:
        manifest = self.manifest_store.read_latest(project_id)
        if manifest is None:
            graph = ProjectGraph(
                project_id=project_id,
                nodes=[
                    GraphNode(
                        id=_node_id(project_id, "project", project_id),
                        label=NodeLabel.PROJECT,
                        properties={"project_id": project_id, "status": "empty"},
                    )
                ],
                warnings=[f"{project_id}: no ingestion manifest found"],
            )
        else:
            graph = self.build_from_manifest(project_id, manifest)

        write_status = self.adapter.rebuild_graph(graph)
        return {
            "project_id": project_id,
            "node_count": graph.node_count,
            "edge_count": graph.edge_count,
            "warnings": graph.warnings,
            "graph": graph.model_dump(mode="json"),
            "storage": write_status,
        }

    def build_from_manifest(self, project_id: str, manifest: dict[str, Any]) -> ProjectGraph:
        nodes: list[GraphNode] = [
            GraphNode(
                id=_node_id(project_id, "project", project_id),
                label=NodeLabel.PROJECT,
                properties={
                    "project_id": project_id,
                    "manifest_created_at": manifest.get("created_at"),
                    "files_processed": manifest.get("files_processed", 0),
                    "chunks_indexed": manifest.get("chunks_indexed", 0),
                    "manifest_path": manifest.get("path"),
                },
            )
        ]
        edges: list[GraphEdge] = []
        warnings = list(manifest.get("warnings", []))
        project_node_id = nodes[0].id

        for document_index, document in enumerate(manifest.get("documents", []), start=1):
            source = document.get("source", f"document-{document_index}")
            document_metadata = dict(document.get("metadata", {}))
            document_node_id = _node_id(project_id, "document", source)
            nodes.append(
                GraphNode(
                    id=document_node_id,
                    label=NodeLabel.DOCUMENT,
                    properties={
                        "project_id": project_id,
                        "source": source,
                        "parser": document_metadata.get("parser"),
                        "source_hash": document_metadata.get("source_hash"),
                        "chunk_count": document_metadata.get("chunk_count", 0),
                        "warnings": document.get("warnings", []),
                        "metadata": document_metadata,
                    },
                )
            )
            edges.append(
                GraphEdge(
                    source_id=project_node_id,
                    target_id=document_node_id,
                    type=EdgeType.HAS_DOCUMENT,
                    properties={
                        "provenance": "ingestion_manifest",
                        "document_index": document_index,
                    },
                )
            )

            for chunk_index, chunk_metadata in enumerate(document.get("chunks", []), start=1):
                chunk_node_id = _node_id(project_id, "chunk", source, str(chunk_index))
                nodes.append(
                    GraphNode(
                        id=chunk_node_id,
                        label=NodeLabel.CHUNK,
                        properties={
                            "project_id": project_id,
                            "source": source,
                            "parser": chunk_metadata.get("parser"),
                            "source_hash": chunk_metadata.get("source_hash"),
                            "page": chunk_metadata.get("page"),
                            "chunk_index": chunk_metadata.get("chunk_index", chunk_index),
                            "chunk_size": chunk_metadata.get("chunk_size"),
                            "metadata": chunk_metadata,
                        },
                    )
                )
                edges.append(
                    GraphEdge(
                        source_id=document_node_id,
                        target_id=chunk_node_id,
                        type=EdgeType.HAS_CHUNK,
                        properties={
                            "provenance": "ingestion_manifest",
                            "source_hash": chunk_metadata.get("source_hash"),
                        },
                    )
                )

        return ProjectGraph(project_id=project_id, nodes=nodes, edges=edges, warnings=warnings)

    def get_graph(self, project_id: str) -> dict[str, Any]:
        graph = self.adapter.get_graph(project_id)
        if graph is None:
            return {
                "project_id": project_id,
                "node_count": 0,
                "edge_count": 0,
                "warnings": [f"{project_id}: graph has not been built"],
                "graph": {"project_id": project_id, "nodes": [], "edges": [], "warnings": []},
                "storage": self.adapter.status(),
            }
        return {
            "project_id": project_id,
            "node_count": graph.node_count,
            "edge_count": graph.edge_count,
            "warnings": graph.warnings,
            "graph": graph.model_dump(mode="json"),
            "storage": self.adapter.status(),
        }

    def status(self, project_id: str) -> dict[str, Any]:
        graph = self.adapter.get_graph(project_id)
        return {
            "project_id": project_id,
            "built": graph is not None,
            "node_count": graph.node_count if graph else 0,
            "edge_count": graph.edge_count if graph else 0,
            "storage": self.adapter.status(),
        }


