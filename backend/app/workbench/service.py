from typing import Any

from graph.builder import ProjectGraphBuilder
from storage.locus_adapter import LocusAdapter


class WorkbenchService:
    def __init__(
        self,
        graph_builder: ProjectGraphBuilder | None = None,
    ):
        self.graph_builder = graph_builder or ProjectGraphBuilder()

    async def query(self, project_id: str, query: str, limit: int = 5) -> dict[str, Any]:
        locus = LocusAdapter(project_id)
        graph = self.graph_builder.get_graph(project_id)
        context = await locus.retrieve(query, limit=limit)
        sources = _document_sources(graph)
        chunks = _normalize_context(context)

        return {
            "project_id": project_id,
            "query": query,
            "answer": _compose_answer(query, chunks, graph, sources),
            "context": chunks,
            "graph": {
                "built": graph.get("node_count", 0) > 0,
                "node_count": graph.get("node_count", 0),
                "edge_count": graph.get("edge_count", 0),
                "sources": sources,
            },
            "storage": {
                "locus": locus.status(),
            },
        }


def _document_sources(graph: dict[str, Any]) -> list[str]:
    sources: list[str] = []
    for node in graph.get("graph", {}).get("nodes", []):
        if node.get("label") != "Document":
            continue
        source = node.get("properties", {}).get("source")
        if source:
            sources.append(source)
    return sources


def _normalize_context(context: Any) -> list[dict[str, Any]]:
    if not context:
        return []
    if not isinstance(context, list):
        context = [context]

    normalized: list[dict[str, Any]] = []
    for item in context:
        if isinstance(item, dict):
            normalized.append(
                {
                    "source": item.get("source", "unknown"),
                    "text": item.get("text", ""),
                    "metadata": item.get("metadata", {}),
                }
            )
        else:
            normalized.append({"source": "unknown", "text": str(item), "metadata": {}})
    return normalized


def _compose_answer(
    query: str,
    chunks: list[dict[str, Any]],
    graph: dict[str, Any],
    sources: list[str],
) -> str:
    if chunks:
        preview = chunks[0]["text"][:240].strip() or "Retrieved chunk has no text content."
        return (
            f"Grounded response for '{query}': found {len(chunks)} Locus context item(s) "
            f"across {len(sources)} graph document source(s). Top excerpt: {preview}"
        )

    if graph.get("node_count", 0) > 0:
        return (
            f"No Locus chunks matched '{query}', but the project graph contains "
            f"{graph['node_count']} nodes from {len(sources)} document source(s)."
        )

    return (
        f"No grounded context found for '{query}'. Upload project documents and build the graph first."
    )
