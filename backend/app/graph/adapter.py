from typing import Any

from core.config import settings
from graph.models import GraphEdge, GraphNode, ProjectGraph


class GraphAdapterError(RuntimeError):
    pass


class InMemoryGraphStore:
    _graphs: dict[str, ProjectGraph] = {}

    def upsert_graph(self, graph: ProjectGraph) -> None:
        self._graphs[graph.project_id] = graph

    def get_graph(self, project_id: str) -> ProjectGraph | None:
        return self._graphs.get(project_id)

    def status(self) -> dict[str, Any]:
        return {
            "backend": "memory",
            "native": False,
            "project_count": len(self._graphs),
        }


class Neo4jGraphAdapter:
    _native_disabled_warning: str | None = None

    def __init__(self):
        self.native = True
        self.warning: str | None = self.__class__._native_disabled_warning
        self._memory = InMemoryGraphStore()
        self._driver = None

        if self.warning and not settings.REQUIRE_NATIVE_NEO4J:
            self.native = False
            return

        try:
            from neo4j import GraphDatabase

            self._driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
                connection_timeout=settings.NEO4J_CONNECTION_TIMEOUT,
            )
        except Exception as exc:
            if settings.REQUIRE_NATIVE_NEO4J:
                raise GraphAdapterError(f"Neo4j unavailable: {exc}") from exc
            self.native = False
            self.warning = str(exc)
            self.__class__._native_disabled_warning = self.warning

    def close(self) -> None:
        if self._driver is not None:
            self._driver.close()

    def upsert_graph(self, graph: ProjectGraph) -> dict[str, Any]:
        if self._driver is None:
            self._memory.upsert_graph(graph)
            return self.status() | {"node_count": graph.node_count, "edge_count": graph.edge_count}

        try:
            with self._driver.session() as session:
                session.execute_write(self._upsert_graph_tx, graph)
        except Exception as exc:
            if settings.REQUIRE_NATIVE_NEO4J:
                raise GraphAdapterError(f"Neo4j write failed: {exc}") from exc
            self.native = False
            self.warning = str(exc)
            self.__class__._native_disabled_warning = self.warning
            self._memory.upsert_graph(graph)

        return self.status() | {"node_count": graph.node_count, "edge_count": graph.edge_count}

    def get_graph(self, project_id: str) -> ProjectGraph | None:
        memory_graph = self._memory.get_graph(project_id)
        if memory_graph is not None or self._driver is None:
            return memory_graph

        try:
            with self._driver.session() as session:
                return session.execute_read(self._read_graph_tx, project_id)
        except Exception as exc:
            if settings.REQUIRE_NATIVE_NEO4J:
                raise GraphAdapterError(f"Neo4j read failed: {exc}") from exc
            self.native = False
            self.warning = str(exc)
            self.__class__._native_disabled_warning = self.warning
            return None

    def status(self) -> dict[str, Any]:
        if self._driver is None:
            status = self._memory.status()
            status["warning"] = self.warning
            return status
        return {
            "backend": "neo4j",
            "native": self.native,
            "uri": settings.NEO4J_URI,
            "warning": self.warning,
        }

    @staticmethod
    def _upsert_graph_tx(tx, graph: ProjectGraph) -> None:
        for node in graph.nodes:
            Neo4jGraphAdapter._upsert_node(tx, node)
        for edge in graph.edges:
            edge_type = edge.type.value
            tx.run(
                f"""
                MATCH (source {id: $source_id})
                MATCH (target {id: $target_id})
                MERGE (source)-[rel:{edge_type}]->(target)
                SET rel += $properties
                """,
                source_id=edge.source_id,
                target_id=edge.target_id,
                properties=edge.properties,
            )

    @staticmethod
    def _upsert_node(tx, node: GraphNode) -> None:
        label = node.label.value
        tx.run(
            f"MERGE (n:{label} {{id: $id}}) SET n += $properties",
            id=node.id,
            properties=node.properties,
        )

    @staticmethod
    def _read_graph_tx(tx, project_id: str) -> ProjectGraph:
        node_records = tx.run(
            """
            MATCH (n {project_id: $project_id})
            RETURN DISTINCT labels(n) AS labels, properties(n) AS properties
            """,
            project_id=project_id,
        )
        nodes = []
        for record in node_records:
            labels = record["labels"]
            properties = dict(record["properties"])
            label = labels[0] if labels else "Document"
            nodes.append(GraphNode(id=properties.pop("id"), label=label, properties=properties))

        edge_records = tx.run(
            """
            MATCH (source {project_id: $project_id})-[r]->(target {project_id: $project_id})
            RETURN DISTINCT source.id AS source_id, target.id AS target_id, type(r) AS type, properties(r) AS properties
            """,
            project_id=project_id,
        )
        edges = [
            GraphEdge(
                source_id=record["source_id"],
                target_id=record["target_id"],
                type=record["type"],
                properties=dict(record["properties"]),
            )
            for record in edge_records
        ]
        return ProjectGraph(project_id=project_id, nodes=nodes, edges=edges)
