from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from app.core.config import Settings


class ProjectGraphStore:
    """Project graph persistence with Neo4j support and in-memory fallback."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._memory: dict[str, dict[str, Any]] = {}
        self._driver = self._build_driver()

    def _build_driver(self):
        try:
            from neo4j import GraphDatabase
        except ImportError:
            return None

        try:
            auth = (self._settings.NEO4J_USER, self._settings.NEO4J_PASSWORD)
            driver = GraphDatabase.driver(self._settings.NEO4J_URI, auth=auth)
            driver.verify_connectivity()
            return driver
        except Exception:
            return None

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(UTC).isoformat()

    @staticmethod
    def _build_graph(
        project_id: str,
        compliance: str,
        ingestion: dict[str, Any] | None,
        orchestration: dict[str, Any] | None,
    ) -> dict[str, Any]:
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []

        project_node_id = f"project:{project_id}"
        nodes.append(
            {
                "id": project_node_id,
                "kind": "project",
                "name": project_id,
                "project_id": project_id,
                "compliance": compliance,
            }
        )

        ingestion_details = (ingestion or {}).get("details", [])
        for idx, detail in enumerate(ingestion_details):
            file_node_id = f"file:{project_id}:{idx}"
            nodes.append(
                {
                    "id": file_node_id,
                    "kind": "file",
                    "name": detail.get("filename") or f"file_{idx}",
                    "project_id": project_id,
                    "parser": detail.get("parser", "unknown"),
                    "chunks": int(detail.get("chunks", 0)),
                }
            )
            edges.append(
                {
                    "id": f"edge:{project_id}:ingested:{idx}",
                    "kind": "ingested",
                    "project_id": project_id,
                    "source": project_node_id,
                    "target": file_node_id,
                }
            )

        states = (orchestration or {}).get("states_visited", [])
        previous_stage_id = None
        for index, stage in enumerate(states):
            stage_id = f"stage:{project_id}:{stage}"
            nodes.append(
                {
                    "id": stage_id,
                    "kind": "workflow_stage",
                    "name": stage,
                    "project_id": project_id,
                    "order": index,
                }
            )
            edges.append(
                {
                    "id": f"edge:{project_id}:stage:{stage}",
                    "kind": "has_stage",
                    "project_id": project_id,
                    "source": project_node_id,
                    "target": stage_id,
                }
            )
            if previous_stage_id:
                edges.append(
                    {
                        "id": f"edge:{project_id}:sequence:{index}",
                        "kind": "next_stage",
                        "project_id": project_id,
                        "source": previous_stage_id,
                        "target": stage_id,
                    }
                )
            previous_stage_id = stage_id

        for idx, template in enumerate((orchestration or {}).get("templates", [])):
            template_id = f"template:{project_id}:{idx}"
            nodes.append(
                {
                    "id": template_id,
                    "kind": "template",
                    "name": template.get("name", f"template_{idx}"),
                    "project_id": project_id,
                    "status": template.get("status", "unknown"),
                }
            )
            if previous_stage_id:
                edges.append(
                    {
                        "id": f"edge:{project_id}:template:{idx}",
                        "kind": "generated",
                        "project_id": project_id,
                        "source": previous_stage_id,
                        "target": template_id,
                    }
                )

        return {
            "project_id": project_id,
            "nodes": nodes,
            "edges": edges,
            "summary": {
                "project_id": project_id,
                "nodes": len(nodes),
                "edges": len(edges),
            },
        }

    def _persist_neo4j(self, graph: dict[str, Any]) -> None:
        if not self._driver:
            return

        now = self._now_iso()
        try:
            with self._driver.session() as session:
                for node in graph["nodes"]:
                    payload = dict(node)
                    node_id = payload.pop("id")
                    node_kind = payload.pop("kind")
                    project_id = payload.get("project_id", graph["project_id"])
                    session.run(
                        """
                        MERGE (n:ProjectGraphNode {id: $id})
                        SET n.kind = $kind,
                            n.project_id = $project_id,
                            n.payload = $payload,
                            n.updated_at = $updated_at
                        """,
                        id=node_id,
                        kind=node_kind,
                        project_id=project_id,
                        payload=json.dumps(payload),
                        updated_at=now,
                    )

                for edge in graph["edges"]:
                    payload = dict(edge)
                    edge_id = payload.pop("id")
                    edge_kind = payload.pop("kind")
                    source = payload.pop("source")
                    target = payload.pop("target")
                    project_id = payload.get("project_id", graph["project_id"])
                    session.run(
                        """
                        MATCH (s:ProjectGraphNode {id: $source}), (t:ProjectGraphNode {id: $target})
                        MERGE (s)-[r:PROJECT_GRAPH_EDGE {id: $id}]->(t)
                        SET r.kind = $kind,
                            r.project_id = $project_id,
                            r.payload = $payload,
                            r.updated_at = $updated_at
                        """,
                        source=source,
                        target=target,
                        id=edge_id,
                        kind=edge_kind,
                        project_id=project_id,
                        payload=json.dumps(payload),
                        updated_at=now,
                    )
        except Exception:
            # Connection issues should not block API responses in fallback mode.
            self._driver = None

    async def upsert_project_graph(
        self,
        project_id: str,
        compliance: str = "standard",
        ingestion: dict[str, Any] | None = None,
        orchestration: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        graph = self._build_graph(
            project_id=project_id,
            compliance=compliance,
            ingestion=ingestion,
            orchestration=orchestration,
        )
        self._memory[project_id] = graph
        self._persist_neo4j(graph)

        backend = "neo4j" if self._driver else "in_memory"
        summary = dict(graph["summary"])
        summary["backend"] = backend
        return summary

    async def get_summary(self, project_id: str) -> dict[str, Any]:
        graph = self._memory.get(project_id)
        if not graph:
            return {"project_id": project_id, "status": "not_found", "nodes": 0, "edges": 0}
        summary = dict(graph["summary"])
        summary["status"] = "ok"
        summary["backend"] = "neo4j" if self._driver else "in_memory"
        return summary

    async def get_nodes(self, project_id: str) -> dict[str, Any]:
        graph = self._memory.get(project_id)
        if not graph:
            return {"project_id": project_id, "status": "not_found", "nodes": []}
        return {"project_id": project_id, "status": "ok", "nodes": graph["nodes"]}

    async def get_edges(self, project_id: str) -> dict[str, Any]:
        graph = self._memory.get(project_id)
        if not graph:
            return {"project_id": project_id, "status": "not_found", "edges": []}
        return {"project_id": project_id, "status": "ok", "edges": graph["edges"]}
