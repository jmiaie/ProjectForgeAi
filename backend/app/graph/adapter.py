"""Graph storage adapters.

Two backends are supported behind a single :class:`GraphAdapter` interface:

* :class:`Neo4jGraphAdapter` — uses the official ``neo4j`` async driver. Each
  project lives in its own logical namespace via a ``project_id`` property on
  every node (the canonical Cypher pattern for multi-tenant graphs).
* :class:`InMemoryGraphAdapter` — JSON-on-disk store used by tests, by local
  development without a Neo4j instance, and as a graceful fallback when the
  driver fails to connect.

The factory :func:`get_graph_adapter` consults ``Settings.GRAPH_BACKEND`` and
returns the configured adapter.
"""

from __future__ import annotations

import json
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Iterable

from app.core.config import Settings, get_settings
from app.graph.schema import Edge, EdgeKind, Node, NodeKind

logger = logging.getLogger(__name__)

try:  # pragma: no cover - optional dependency
    from neo4j import AsyncGraphDatabase  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    AsyncGraphDatabase = None  # type: ignore[assignment]


@dataclass
class GraphSnapshot:
    project_id: str
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)

    def stats(self) -> dict[str, Any]:
        node_counts: dict[str, int] = {}
        for node in self.nodes:
            node_counts[node.kind.value] = node_counts.get(node.kind.value, 0) + 1
        edge_counts: dict[str, int] = {}
        for edge in self.edges:
            edge_counts[edge.kind.value] = edge_counts.get(edge.kind.value, 0) + 1
        return {
            "project_id": self.project_id,
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "nodes_by_kind": node_counts,
            "edges_by_kind": edge_counts,
        }

    def to_react_flow(self) -> dict[str, Any]:
        """Return a React Flow-friendly payload.

        We assign deterministic radial positions per node kind so a simple
        front-end can render the graph immediately. Real layouts (dagre /
        elk / force-directed) can be applied client-side.
        """

        groups: dict[str, list[Node]] = {}
        for node in self.nodes:
            groups.setdefault(node.kind.value, []).append(node)

        rf_nodes: list[dict[str, Any]] = []
        column_x_step = 280
        row_y_step = 120
        for col_index, (kind, nodes) in enumerate(sorted(groups.items())):
            for row_index, node in enumerate(nodes):
                rf_nodes.append(
                    {
                        "id": node.id,
                        "type": "default",
                        "position": {
                            "x": col_index * column_x_step,
                            "y": row_index * row_y_step,
                        },
                        "data": {
                            "label": node.label,
                            "kind": kind,
                            "properties": node.properties,
                        },
                    }
                )

        rf_edges = [
            {
                "id": edge.id,
                "source": edge.source,
                "target": edge.target,
                "label": edge.kind.value,
                "animated": edge.kind in {EdgeKind.DEPENDS_ON, EdgeKind.MITIGATES},
                "data": edge.properties,
            }
            for edge in self.edges
        ]
        return {"nodes": rf_nodes, "edges": rf_edges}


# ---------------------------------------------------------------------------
# Adapter interface
# ---------------------------------------------------------------------------
class GraphAdapter(ABC):
    @abstractmethod
    async def upsert_nodes(self, project_id: str, nodes: Iterable[Node]) -> None: ...

    @abstractmethod
    async def upsert_edges(self, project_id: str, edges: Iterable[Edge]) -> None: ...

    @abstractmethod
    async def get_snapshot(self, project_id: str) -> GraphSnapshot: ...

    @abstractmethod
    async def get_node(self, project_id: str, node_id: str) -> Node | None: ...

    @abstractmethod
    async def clear_project(self, project_id: str) -> None: ...

    async def close(self) -> None:  # pragma: no cover - default no-op
        return None


# ---------------------------------------------------------------------------
# In-memory / file-backed adapter
# ---------------------------------------------------------------------------
class InMemoryGraphAdapter(GraphAdapter):
    """JSON-per-project store under ``Settings.GRAPH_DATA_ROOT``.

    Good enough for local dev, tests, and as a fallback when Neo4j is down.
    """

    def __init__(self, root: str | None = None) -> None:
        settings = get_settings()
        self.root = root or settings.GRAPH_DATA_ROOT
        os.makedirs(self.root, exist_ok=True)

    def _path(self, project_id: str) -> str:
        return os.path.join(self.root, f"project_{project_id}.json")

    def _load(self, project_id: str) -> dict[str, Any]:
        path = self._path(project_id)
        if not os.path.exists(path):
            return {"nodes": {}, "edges": {}}
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)

    def _save(self, project_id: str, data: dict[str, Any]) -> None:
        with open(self._path(project_id), "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)

    async def upsert_nodes(self, project_id: str, nodes: Iterable[Node]) -> None:
        data = self._load(project_id)
        for node in nodes:
            data["nodes"][node.id] = node.to_dict()
        self._save(project_id, data)

    async def upsert_edges(self, project_id: str, edges: Iterable[Edge]) -> None:
        data = self._load(project_id)
        for edge in edges:
            data["edges"][edge.id] = edge.to_dict()
        self._save(project_id, data)

    async def get_snapshot(self, project_id: str) -> GraphSnapshot:
        data = self._load(project_id)
        nodes = [Node.from_dict(payload) for payload in data["nodes"].values()]
        edges = [Edge.from_dict(payload) for payload in data["edges"].values()]
        return GraphSnapshot(project_id=project_id, nodes=nodes, edges=edges)

    async def get_node(self, project_id: str, node_id: str) -> Node | None:
        data = self._load(project_id)
        payload = data["nodes"].get(node_id)
        return Node.from_dict(payload) if payload is not None else None

    async def clear_project(self, project_id: str) -> None:
        path = self._path(project_id)
        if os.path.exists(path):
            os.remove(path)


# ---------------------------------------------------------------------------
# Neo4j adapter
# ---------------------------------------------------------------------------
class Neo4jGraphAdapter(GraphAdapter):
    """Neo4j-backed implementation using the async driver."""

    def __init__(self, settings: Settings | None = None) -> None:
        if AsyncGraphDatabase is None:  # pragma: no cover
            raise RuntimeError("neo4j driver is not installed")
        self.settings = settings or get_settings()
        self._driver = AsyncGraphDatabase.driver(
            self.settings.NEO4J_URI,
            auth=(self.settings.NEO4J_USER, self.settings.NEO4J_PASSWORD),
        )

    async def close(self) -> None:  # pragma: no cover - exercised via real driver
        await self._driver.close()

    async def upsert_nodes(self, project_id: str, nodes: Iterable[Node]) -> None:  # pragma: no cover
        async with self._driver.session() as session:
            for node in nodes:
                cypher = (
                    "MERGE (n {id: $id, project_id: $project_id}) "
                    "SET n :`%s`, n.label = $label, n += $properties"
                ) % node.kind.value
                await session.run(
                    cypher,
                    id=node.id,
                    project_id=project_id,
                    label=node.label,
                    properties=node.properties,
                )

    async def upsert_edges(self, project_id: str, edges: Iterable[Edge]) -> None:  # pragma: no cover
        async with self._driver.session() as session:
            for edge in edges:
                cypher = (
                    "MATCH (a {id: $source, project_id: $project_id}), "
                    "      (b {id: $target, project_id: $project_id}) "
                    "MERGE (a)-[r:`%s` {id: $id}]->(b) "
                    "SET r += $properties"
                ) % edge.kind.value
                await session.run(
                    cypher,
                    id=edge.id,
                    source=edge.source,
                    target=edge.target,
                    project_id=project_id,
                    properties=edge.properties,
                )

    async def get_snapshot(self, project_id: str) -> GraphSnapshot:  # pragma: no cover
        async with self._driver.session() as session:
            node_result = await session.run(
                "MATCH (n {project_id: $project_id}) RETURN n",
                project_id=project_id,
            )
            nodes: list[Node] = []
            async for record in node_result:
                raw = dict(record["n"])
                kind_label = next(iter(record["n"].labels), NodeKind.PROJECT.value)
                nodes.append(
                    Node(
                        id=raw.pop("id"),
                        kind=NodeKind(kind_label),
                        label=raw.pop("label", ""),
                        properties={k: v for k, v in raw.items() if k != "project_id"},
                    )
                )

            edge_result = await session.run(
                "MATCH (a {project_id: $project_id})-[r]->(b {project_id: $project_id}) "
                "RETURN r, a.id AS source, b.id AS target",
                project_id=project_id,
            )
            edges: list[Edge] = []
            async for record in edge_result:
                rel = record["r"]
                props = dict(rel)
                edges.append(
                    Edge(
                        id=props.pop("id", str(rel.id)),
                        source=record["source"],
                        target=record["target"],
                        kind=EdgeKind(rel.type),
                        properties=props,
                    )
                )
        return GraphSnapshot(project_id=project_id, nodes=nodes, edges=edges)

    async def get_node(self, project_id: str, node_id: str) -> Node | None:  # pragma: no cover
        snapshot = await self.get_snapshot(project_id)
        for node in snapshot.nodes:
            if node.id == node_id:
                return node
        return None

    async def clear_project(self, project_id: str) -> None:  # pragma: no cover
        async with self._driver.session() as session:
            await session.run(
                "MATCH (n {project_id: $project_id}) DETACH DELETE n",
                project_id=project_id,
            )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
_DEFAULT_ADAPTER: GraphAdapter | None = None


def get_graph_adapter() -> GraphAdapter:
    """Return the configured graph adapter, building it lazily."""

    global _DEFAULT_ADAPTER
    if _DEFAULT_ADAPTER is not None:
        return _DEFAULT_ADAPTER

    settings = get_settings()
    backend = settings.GRAPH_BACKEND.lower()
    if backend == "neo4j":
        if AsyncGraphDatabase is None:
            logger.warning(
                "GRAPH_BACKEND=neo4j but the driver is not installed; "
                "falling back to in-memory graph"
            )
            _DEFAULT_ADAPTER = InMemoryGraphAdapter()
        else:
            try:
                _DEFAULT_ADAPTER = Neo4jGraphAdapter(settings)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("Neo4j adapter init failed (%s); using in-memory", exc)
                _DEFAULT_ADAPTER = InMemoryGraphAdapter()
    else:
        _DEFAULT_ADAPTER = InMemoryGraphAdapter()
    return _DEFAULT_ADAPTER


def reset_graph_adapter() -> None:
    """Drop the cached adapter (used by tests)."""

    global _DEFAULT_ADAPTER
    _DEFAULT_ADAPTER = None
