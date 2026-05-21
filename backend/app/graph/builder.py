"""Project graph builder.

Translates ingestion summaries and orchestrator outputs into nodes/edges and
hands them to whichever :class:`~app.graph.adapter.GraphAdapter` is active.
"""

from __future__ import annotations

import hashlib
from typing import Any

from app.graph.adapter import GraphAdapter, GraphSnapshot, get_graph_adapter
from app.graph.schema import Edge, EdgeKind, Node, NodeKind


def _node_id(project_id: str, kind: NodeKind, key: str) -> str:
    digest = hashlib.sha1(f"{project_id}:{kind.value}:{key}".encode("utf-8")).hexdigest()[:12]
    return f"{kind.value.lower()}_{digest}"


def _edge_id(source: str, target: str, kind: EdgeKind) -> str:
    digest = hashlib.sha1(f"{source}:{target}:{kind.value}".encode("utf-8")).hexdigest()[:12]
    return f"e_{digest}"


class GraphBuilder:
    """Stateful helper that mutates the graph for a single project."""

    def __init__(self, project_id: str, adapter: GraphAdapter | None = None) -> None:
        self.project_id = project_id
        self.adapter = adapter or get_graph_adapter()

    # ------------------------------------------------------------------
    # Project / connections
    # ------------------------------------------------------------------
    async def add_project(
        self,
        name: str,
        compliance: str = "standard",
        objective: str | None = None,
    ) -> Node:
        node = Node(
            id=self.project_id,
            kind=NodeKind.PROJECT,
            label=name,
            properties={
                "compliance": compliance,
                "objective": objective or "",
            },
        )
        await self.adapter.upsert_nodes(self.project_id, [node])
        return node

    async def add_connection(
        self,
        connection_id: str,
        connector_type: str,
        provider: str | None = None,
        scopes: list[str] | None = None,
    ) -> None:
        node = Node(
            id=connection_id,
            kind=NodeKind.CONNECTION,
            label=f"{connector_type}",
            properties={
                "connector_type": connector_type,
                "provider": provider or connector_type,
                "scopes": scopes or [],
            },
        )
        edge = Edge(
            id=_edge_id(self.project_id, connection_id, EdgeKind.CONNECTED_VIA),
            source=self.project_id,
            target=connection_id,
            kind=EdgeKind.CONNECTED_VIA,
        )
        await self.adapter.upsert_nodes(self.project_id, [node])
        await self.adapter.upsert_edges(self.project_id, [edge])

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------
    async def add_documents_from_ingestion(
        self, ingestion_summary: dict[str, Any]
    ) -> dict[str, int]:
        nodes: list[Node] = []
        edges: list[Edge] = []
        chunk_count = 0
        for file_entry in ingestion_summary.get("files", []):
            filename = file_entry.get("file") or "unknown"
            doc_id = _node_id(self.project_id, NodeKind.DOCUMENT, filename)
            nodes.append(
                Node(
                    id=doc_id,
                    kind=NodeKind.DOCUMENT,
                    label=filename,
                    properties={
                        "parser": file_entry.get("parser"),
                        "chunks": file_entry.get("chunks", 0),
                        "warnings": file_entry.get("warnings", []),
                    },
                )
            )
            edges.append(
                Edge(
                    id=_edge_id(self.project_id, doc_id, EdgeKind.HAS_DOCUMENT),
                    source=self.project_id,
                    target=doc_id,
                    kind=EdgeKind.HAS_DOCUMENT,
                )
            )
            for index in range(file_entry.get("chunks", 0)):
                chunk_id = _node_id(
                    self.project_id, NodeKind.CHUNK, f"{filename}:{index}"
                )
                nodes.append(
                    Node(
                        id=chunk_id,
                        kind=NodeKind.CHUNK,
                        label=f"{filename}#{index + 1}",
                        properties={"index": index, "document": filename},
                    )
                )
                edges.append(
                    Edge(
                        id=_edge_id(doc_id, chunk_id, EdgeKind.CONTAINS_CHUNK),
                        source=doc_id,
                        target=chunk_id,
                        kind=EdgeKind.CONTAINS_CHUNK,
                    )
                )
                chunk_count += 1

        if nodes:
            await self.adapter.upsert_nodes(self.project_id, nodes)
        if edges:
            await self.adapter.upsert_edges(self.project_id, edges)
        return {"documents": len(nodes) - chunk_count, "chunks": chunk_count}

    # ------------------------------------------------------------------
    # Orchestrator outputs
    # ------------------------------------------------------------------
    async def add_orchestrator_outputs(
        self, outputs: dict[str, Any]
    ) -> dict[str, int]:
        """Translate specialist artefacts into nodes + edges."""

        nodes: list[Node] = []
        edges: list[Edge] = []
        counts: dict[str, int] = {}

        for agent_name, output in outputs.items():
            artefacts = output.get("artefacts", []) if isinstance(output, dict) else []
            for artefact in artefacts:
                kind, label = self._classify_artefact(agent_name, artefact)
                if kind is None:
                    continue
                node_key = artefact.get("value") or artefact.get("label") or label
                node_id = _node_id(self.project_id, kind, f"{agent_name}:{node_key}")
                nodes.append(
                    Node(
                        id=node_id,
                        kind=kind,
                        label=label,
                        properties={
                            **{k: v for k, v in artefact.items() if k != "kind"},
                            "produced_by": agent_name,
                        },
                    )
                )
                edges.append(
                    Edge(
                        id=_edge_id(self.project_id, node_id, EdgeKind.GENERATED),
                        source=self.project_id,
                        target=node_id,
                        kind=EdgeKind.GENERATED,
                        properties={"agent": agent_name},
                    )
                )
                counts[kind.value] = counts.get(kind.value, 0) + 1

        if nodes:
            await self.adapter.upsert_nodes(self.project_id, nodes)
        if edges:
            await self.adapter.upsert_edges(self.project_id, edges)
        return counts

    def _classify_artefact(
        self, agent_name: str, artefact: dict[str, Any]
    ) -> tuple[NodeKind | None, str]:
        kind_hint = (artefact.get("kind") or "").lower()
        value = str(artefact.get("value") or artefact.get("label") or "")[:120]

        if kind_hint == "milestone":
            return NodeKind.MILESTONE, value or "Milestone"
        if kind_hint in {"task", "schedule_item"}:
            return NodeKind.TASK, value or "Task"
        if kind_hint == "risk":
            return NodeKind.RISK, value or "Risk"
        if kind_hint == "compliance_control":
            return NodeKind.CONTROL, value or "Control"
        if kind_hint == "contract_template":
            label = artefact.get("label", "contract")
            return NodeKind.CONTRACT, str(label).upper() if label else "Contract"
        if kind_hint == "comms_template":
            label = artefact.get("label", "template")
            return NodeKind.COMMS_TEMPLATE, str(label).replace("_", " ").title()
        return None, ""

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    async def snapshot(self) -> GraphSnapshot:
        return await self.adapter.get_snapshot(self.project_id)
