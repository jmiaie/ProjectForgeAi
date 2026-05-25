from typing import Any

from graph.builder import ProjectGraphBuilder
from graph.extraction import ExtractedFact, extract_facts
from graph.ids import make_node_id
from graph.models import EdgeType, GraphEdge, GraphNode, NodeLabel, ProjectGraph
from storage.locus_adapter import InMemoryLocusEngine, LocusAdapter


class GraphEnrichmentService:
    def __init__(self, builder: ProjectGraphBuilder | None = None):
        self.builder = builder or ProjectGraphBuilder()

    async def enrich(self, project_id: str, use_llm: bool = False) -> dict[str, Any]:
        current = self.builder.get_graph(project_id)
        if current["node_count"] == 0:
            self.builder.build_from_latest_manifest(project_id)
            current = self.builder.get_graph(project_id)

        graph = ProjectGraph.model_validate(
            {
                "project_id": project_id,
                "nodes": current["graph"]["nodes"],
                "edges": current["graph"]["edges"],
                "warnings": current["graph"].get("warnings", []),
            }
        )

        chunks = await self._collect_chunks(project_id)
        if not chunks:
            graph.warnings.append(f"{project_id}: no indexed chunks available for enrichment")
            self.builder.adapter.upsert_graph(graph)
            return self._result(project_id, graph, added_nodes=0, added_edges=0, facts=[])

        facts: list[ExtractedFact] = []
        for chunk in chunks:
            facts.extend(await extract_facts(chunk, project_id=project_id, use_llm=use_llm))

        added_nodes, added_edges = self._merge_facts(graph, facts)
        write_status = self.builder.adapter.upsert_graph(graph)
        return self._result(
            project_id,
            graph,
            added_nodes=added_nodes,
            added_edges=added_edges,
            facts=facts,
            storage=write_status,
        )

    async def _collect_chunks(self, project_id: str) -> list[dict[str, Any]]:
        locus = LocusAdapter(project_id)
        if isinstance(locus.engine, InMemoryLocusEngine):
            raw = list(locus.engine._stores.get(locus.store_path, []))
        else:
            listed = getattr(locus.engine, "list", None)
            raw = listed() if callable(listed) else []

        chunks: list[dict[str, Any]] = []
        for item in raw:
            if isinstance(item, dict):
                chunks.append(item)
            else:
                chunks.append({"source": "unknown", "text": str(item), "metadata": {}})
        return chunks

    def _merge_facts(self, graph: ProjectGraph, facts: list[ExtractedFact]) -> tuple[int, int]:
        if not graph.nodes:
            return 0, 0

        project_nodes = [node for node in graph.nodes if node.label == NodeLabel.PROJECT]
        if not project_nodes:
            return 0, 0

        project_node_id = project_nodes[0].id
        existing_ids = {node.id for node in graph.nodes}
        chunk_lookup = {
            (
                node.properties.get("source_hash"),
                node.properties.get("chunk_index"),
            ): node.id
            for node in graph.nodes
            if node.label == NodeLabel.CHUNK
        }

        added_nodes = 0
        added_edges = 0
        for fact in facts:
            label = NodeLabel(fact.label)
            node_id = make_node_id(graph.project_id, fact.label.lower(), fact.name, fact.source)
            if node_id in existing_ids:
                continue

            properties = {
                "project_id": graph.project_id,
                "name": fact.name,
                "source": fact.source,
                "source_hash": fact.source_hash,
                "chunk_index": fact.chunk_index,
                "excerpt": fact.excerpt,
                "extractor": fact.extractor,
            }
            if fact.sequence is not None:
                properties["sequence"] = fact.sequence
            if fact.severity:
                properties["severity"] = fact.severity

            graph.nodes.append(GraphNode(id=node_id, label=label, properties=properties))
            existing_ids.add(node_id)
            added_nodes += 1

            graph.edges.append(
                GraphEdge(
                    source_id=project_node_id,
                    target_id=node_id,
                    type=EdgeType.RELATES_TO,
                    properties={"relationship": label.value.lower(), "provenance": "graph_enrichment"},
                )
            )
            added_edges += 1

            chunk_id = chunk_lookup.get((fact.source_hash, fact.chunk_index))
            if chunk_id:
                graph.edges.append(
                    GraphEdge(
                        source_id=node_id,
                        target_id=chunk_id,
                        type=EdgeType.DERIVED_FROM,
                        properties={
                            "provenance": "graph_enrichment",
                            "source_hash": fact.source_hash,
                            "chunk_index": fact.chunk_index,
                        },
                    )
                )
                added_edges += 1

        return added_nodes, added_edges

    def _result(
        self,
        project_id: str,
        graph: ProjectGraph,
        *,
        added_nodes: int,
        added_edges: int,
        facts: list[ExtractedFact],
        storage: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "project_id": project_id,
            "node_count": graph.node_count,
            "edge_count": graph.edge_count,
            "added_nodes": added_nodes,
            "added_edges": added_edges,
            "facts_extracted": len(facts),
            "facts": [
                {
                    "label": fact.label,
                    "name": fact.name,
                    "source": fact.source,
                    "source_hash": fact.source_hash,
                    "extractor": fact.extractor,
                }
                for fact in facts
            ],
            "warnings": graph.warnings,
            "graph": graph.model_dump(mode="json"),
            "storage": storage or self.builder.adapter.status(),
        }
