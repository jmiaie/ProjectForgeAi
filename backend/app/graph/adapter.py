from typing import Any

from core.config import settings
from graph.models import EdgeType, GraphEdge, GraphNode, NodeLabel, ProjectGraph


class GraphAdapterError(RuntimeError):
    pass


class InMemoryGraphStore:
    _graphs: dict[str, ProjectGraph] = {}

    def upsert_graph(self, graph: ProjectGraph) -> None:
        self._graphs[graph.project_id] = graph

    def get_graph(self, project_id: str) -> ProjectGraph | None:
        return self._graphs.get(project_id)

    def upsert_node(self, project_id: str, node: GraphNode) -> None:
        graph = self._require_graph(project_id)
        updated_nodes: list[GraphNode] = []
        replaced = False
        for item in graph.nodes:
            if item.id == node.id:
                updated_nodes.append(node)
                replaced = True
            else:
                updated_nodes.append(item)
        if not replaced:
            updated_nodes.append(node)
        graph.nodes = updated_nodes
        self._graphs[project_id] = graph

    def delete_node(self, project_id: str, node_id: str) -> None:
        graph = self._require_graph(project_id)
        graph.nodes = [node for node in graph.nodes if node.id != node_id]
        graph.edges = [
            edge for edge in graph.edges if edge.source_id != node_id and edge.target_id != node_id
        ]
        self._graphs[project_id] = graph

    def upsert_edge(self, project_id: str, edge: GraphEdge) -> None:
        graph = self._require_graph(project_id)
        graph.edges = [
            item
            for item in graph.edges
            if not (
                item.source_id == edge.source_id
                and item.target_id == edge.target_id
                and item.type == edge.type
            )
        ]
        graph.edges.append(edge)
        self._graphs[project_id] = graph

    def delete_edge(self, project_id: str, source_id: str, target_id: str, edge_type: EdgeType) -> None:
        graph = self._require_graph(project_id)
        graph.edges = [
            edge
            for edge in graph.edges
            if not (
                edge.source_id == source_id and edge.target_id == target_id and edge.type == edge_type
            )
        ]
        self._graphs[project_id] = graph

    def _require_graph(self, project_id: str) -> ProjectGraph:
        graph = self._graphs.get(project_id)
        if graph is None:
            graph = ProjectGraph(project_id=project_id)
            self._graphs[project_id] = graph
        return graph

    def status(self) -> dict[str, Any]:
        return {
            "backend": "memory",
            "native": False,
            "project_count": len(self._graphs),
        }


class Neo4jGraphAdapter:
    _native_disabled_warning: str | None = None

    def __init__(self, tenant_id: str | None = None, database: str | None = None, read_uri: str | None = None):
        self.tenant_id = tenant_id
        self.database = database
        self.read_uri = read_uri
        self.native = True
        self.warning: str | None = self.__class__._native_disabled_warning
        self._memory = InMemoryGraphStore()
        self._driver = None
        self._read_driver = None
        self._write_uri: str | None = None
        self._bootstrapped = False

        if self.warning and not settings.REQUIRE_NATIVE_NEO4J:
            self.native = False
            return

        try:
            from neo4j import GraphDatabase

            from tenancy.neo4j_cluster import connect_with_failover

            if settings.NEO4J_CLUSTER_FAILOVER_ENABLED:
                self._driver, self._write_uri = connect_with_failover()
            else:
                self._driver = GraphDatabase.driver(
                    settings.NEO4J_URI,
                    auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
                    connection_timeout=settings.NEO4J_CONNECTION_TIMEOUT,
                )
                self._driver.verify_connectivity()
                self._write_uri = settings.NEO4J_URI
            if read_uri and read_uri != self._write_uri:
                self._read_driver = GraphDatabase.driver(
                    read_uri,
                    auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
                    connection_timeout=settings.NEO4J_CONNECTION_TIMEOUT,
                )
                self._read_driver.verify_connectivity()
            if settings.NEO4J_BOOTSTRAP_ON_CONNECT:
                self.bootstrap()
        except Exception as exc:
            if self._driver is not None:
                self._driver.close()
                self._driver = None
            if self._read_driver is not None:
                self._read_driver.close()
                self._read_driver = None
            if settings.REQUIRE_NATIVE_NEO4J:
                raise GraphAdapterError(f"Neo4j unavailable: {exc}") from exc
            self.native = False
            self.warning = str(exc)
            self.__class__._native_disabled_warning = self.warning

    def close(self) -> None:
        if self._read_driver is not None:
            self._read_driver.close()
        if self._driver is not None:
            self._driver.close()

    def _session(self, *, read_only: bool = False):
        driver = self._read_driver if read_only and self._read_driver is not None else self._driver
        if driver is None:
            raise GraphAdapterError("Neo4j driver unavailable")
        if self.database and settings.NEO4J_TENANT_ISOLATION_ENABLED:
            try:
                return driver.session(database=self.database)
            except Exception:
                return driver.session()
        return driver.session()

    def _node_with_tenant(self, node: GraphNode) -> GraphNode:
        if not self.tenant_id:
            return node
        properties = dict(node.properties)
        properties.setdefault("tenant_id", self.tenant_id)
        return GraphNode(id=node.id, label=node.label, properties=properties)

    def _graph_with_tenant(self, graph: ProjectGraph) -> ProjectGraph:
        if not self.tenant_id:
            return graph
        return ProjectGraph(
            project_id=graph.project_id,
            nodes=[self._node_with_tenant(node) for node in graph.nodes],
            edges=graph.edges,
            warnings=graph.warnings,
        )

    def bootstrap(self) -> dict[str, Any]:
        if self._driver is None:
            return {"status": "skipped", "backend": "memory", "warning": self.warning}
        from graph.bootstrap import bootstrap_neo4j

        result = bootstrap_neo4j(self._driver, database=self.database)
        self._bootstrapped = True
        return result

    def upsert_graph(self, graph: ProjectGraph) -> dict[str, Any]:
        graph = self._graph_with_tenant(graph)
        if self._driver is None:
            self._memory.upsert_graph(graph)
            return self.status() | {"node_count": graph.node_count, "edge_count": graph.edge_count}

        try:
            with self._session() as session:
                session.execute_write(self._upsert_graph_tx, graph)
        except Exception as exc:
            if settings.REQUIRE_NATIVE_NEO4J:
                raise GraphAdapterError(f"Neo4j write failed: {exc}") from exc
            self.native = False
            self.warning = str(exc)
            self.__class__._native_disabled_warning = self.warning
            self._memory.upsert_graph(graph)

        return self.status() | {"node_count": graph.node_count, "edge_count": graph.edge_count}

    def rebuild_graph(self, graph: ProjectGraph) -> dict[str, Any]:
        graph = self._graph_with_tenant(graph)
        if self._driver is None:
            self._memory.upsert_graph(graph)
            return self.status() | {
                "node_count": graph.node_count,
                "edge_count": graph.edge_count,
                "orphans_removed": 0,
            }

        try:
            with self._session() as session:
                removed = session.execute_write(self._rebuild_graph_tx, graph)
        except Exception as exc:
            if settings.REQUIRE_NATIVE_NEO4J:
                raise GraphAdapterError(f"Neo4j rebuild failed: {exc}") from exc
            self.native = False
            self.warning = str(exc)
            self.__class__._native_disabled_warning = self.warning
            self._memory.upsert_graph(graph)
            removed = 0

        return self.status() | {
            "node_count": graph.node_count,
            "edge_count": graph.edge_count,
            "orphans_removed": removed,
        }

    def upsert_node(self, project_id: str, node: GraphNode) -> dict[str, Any]:
        node = self._node_with_tenant(node)
        if self._driver is None:
            self._memory.upsert_node(project_id, node)
            return self.status()

        with self._session() as session:
            session.execute_write(self._upsert_node_tx, node)
        return self.status()

    def delete_node(self, project_id: str, node_id: str) -> dict[str, Any]:
        if self._driver is None:
            self._memory.delete_node(project_id, node_id)
            return self.status()

        with self._session() as session:
            session.execute_write(self._delete_node_tx, project_id, node_id, self.tenant_id)
        return self.status()

    def upsert_edge(self, project_id: str, edge: GraphEdge) -> dict[str, Any]:
        if self._driver is None:
            self._memory.upsert_edge(project_id, edge)
            return self.status()

        with self._session() as session:
            session.execute_write(self._upsert_edge_tx, edge)
        return self.status()

    def delete_edge(
        self,
        project_id: str,
        source_id: str,
        target_id: str,
        edge_type: EdgeType,
    ) -> dict[str, Any]:
        if self._driver is None:
            self._memory.delete_edge(project_id, source_id, target_id, edge_type)
            return self.status()

        with self._session() as session:
            session.execute_write(self._delete_edge_tx, source_id, target_id, edge_type.value)
        return self.status()

    def get_graph(self, project_id: str) -> ProjectGraph | None:
        memory_graph = self._memory.get_graph(project_id)
        if memory_graph is not None or self._driver is None:
            return memory_graph

        try:
            with self._session(read_only=True) as session:
                return session.execute_read(self._read_graph_tx, project_id, self.tenant_id)
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
            status["bootstrapped"] = False
            return status
        return {
            "backend": "neo4j",
            "native": self.native,
            "uri": self._write_uri or settings.NEO4J_URI,
            "read_uri": self.read_uri,
            "read_replica_active": self._read_driver is not None,
            "cluster_failover_enabled": settings.NEO4J_CLUSTER_FAILOVER_ENABLED,
            "database": self.database,
            "tenant_id": self.tenant_id,
            "warning": self.warning,
            "bootstrapped": self._bootstrapped,
        }

    @staticmethod
    def _upsert_graph_tx(tx, graph: ProjectGraph) -> None:
        for node in graph.nodes:
            Neo4jGraphAdapter._upsert_node_tx(tx, node)
        for edge in graph.edges:
            Neo4jGraphAdapter._upsert_edge_tx(tx, edge)

    @staticmethod
    def _rebuild_graph_tx(tx, graph: ProjectGraph) -> int:
        Neo4jGraphAdapter._upsert_graph_tx(tx, graph)
        node_ids = [node.id for node in graph.nodes]
        result = tx.run(
            """
            MATCH (n {project_id: $project_id})
            WHERE NOT n.id IN $node_ids
            WITH collect(n) AS orphans
            FOREACH (node IN orphans | DETACH DELETE node)
            RETURN size(orphans) AS removed
            """,
            project_id=graph.project_id,
            node_ids=node_ids,
        ).single()
        return int(result["removed"] if result else 0)

    @staticmethod
    def _upsert_node_tx(tx, node: GraphNode) -> None:
        label = node.label.value if isinstance(node.label, NodeLabel) else str(node.label)
        properties = {"id": node.id, "label": label, **node.properties}
        tx.run(
            f"MERGE (n:{label} {{id: $id}}) SET n += $properties",
            id=node.id,
            properties=properties,
        )

    @staticmethod
    def _upsert_edge_tx(tx, edge: GraphEdge) -> None:
        edge_type = edge.type.value if isinstance(edge.type, EdgeType) else str(edge.type)
        tx.run(
            f"""
            MATCH (source {{id: $source_id}})
            MATCH (target {{id: $target_id}})
            MERGE (source)-[rel:{edge_type}]->(target)
            SET rel += $properties
            """,
            source_id=edge.source_id,
            target_id=edge.target_id,
            properties=edge.properties,
        )

    @staticmethod
    def _delete_node_tx(tx, project_id: str, node_id: str, tenant_id: str | None = None) -> None:
        if tenant_id:
            tx.run(
                """
                MATCH (n {project_id: $project_id, tenant_id: $tenant_id, id: $node_id})
                DETACH DELETE n
                """,
                project_id=project_id,
                tenant_id=tenant_id,
                node_id=node_id,
            )
            return
        tx.run(
            """
            MATCH (n {project_id: $project_id, id: $node_id})
            DETACH DELETE n
            """,
            project_id=project_id,
            node_id=node_id,
        )

    @staticmethod
    def _delete_edge_tx(tx, source_id: str, target_id: str, edge_type: str) -> None:
        tx.run(
            f"""
            MATCH (source {{id: $source_id}})-[rel:{edge_type}]->(target {{id: $target_id}})
            DELETE rel
            """,
            source_id=source_id,
            target_id=target_id,
        )

    @staticmethod
    def _read_graph_tx(tx, project_id: str, tenant_id: str | None = None) -> ProjectGraph:
        if tenant_id:
            node_records = tx.run(
                """
                MATCH (n {project_id: $project_id, tenant_id: $tenant_id})
                RETURN DISTINCT labels(n) AS labels, properties(n) AS properties
                """,
                project_id=project_id,
                tenant_id=tenant_id,
            )
        else:
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
            node_id = properties.pop("id", None)
            label_value = properties.pop("label", None) or (labels[0] if labels else "Document")
            if node_id is None:
                continue
            nodes.append(GraphNode(id=node_id, label=label_value, properties=properties))

        if tenant_id:
            edge_records = tx.run(
                """
                MATCH (source {project_id: $project_id, tenant_id: $tenant_id})-[r]->(target {project_id: $project_id, tenant_id: $tenant_id})
                RETURN DISTINCT source.id AS source_id, target.id AS target_id, type(r) AS type, properties(r) AS properties
                """,
                project_id=project_id,
                tenant_id=tenant_id,
            )
        else:
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
                properties=dict(record["properties"] or {}),
            )
            for record in edge_records
        ]
        return ProjectGraph(project_id=project_id, nodes=nodes, edges=edges)
