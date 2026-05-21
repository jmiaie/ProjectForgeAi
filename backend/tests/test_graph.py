"""Tests for the project graph layer (schema, builder, adapter, endpoints)."""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient

from app.graph.adapter import (
    InMemoryGraphAdapter,
    get_graph_adapter,
    reset_graph_adapter,
)
from app.graph.builder import GraphBuilder
from app.graph.schema import Edge, EdgeKind, Node, NodeKind
from app.main import app

SAMPLE_EMAIL = b"""From: alice@example.com
To: bob@example.com
Subject: Graph builder kickoff
Date: Wed, 01 Jan 2025 09:00:00 +0000
Content-Type: text/plain

Body for graph builder kickoff.
"""


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
def test_node_round_trips_via_dict() -> None:
    node = Node(
        id="n1",
        kind=NodeKind.RISK,
        label="Vendor delay",
        properties={"likelihood": "medium"},
    )
    assert Node.from_dict(node.to_dict()) == node


def test_edge_round_trips_via_dict() -> None:
    edge = Edge(
        id="e1",
        source="n1",
        target="n2",
        kind=EdgeKind.MITIGATES,
        properties={"strength": "primary"},
    )
    assert Edge.from_dict(edge.to_dict()) == edge


# ---------------------------------------------------------------------------
# In-memory adapter
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_inmemory_adapter_roundtrip(tmp_path) -> None:
    adapter = InMemoryGraphAdapter(root=str(tmp_path))
    project_id = "proj_adapter"
    await adapter.upsert_nodes(
        project_id,
        [
            Node(id="p", kind=NodeKind.PROJECT, label="P"),
            Node(id="d", kind=NodeKind.DOCUMENT, label="D"),
        ],
    )
    await adapter.upsert_edges(
        project_id,
        [Edge(id="e1", source="p", target="d", kind=EdgeKind.HAS_DOCUMENT)],
    )

    snapshot = await adapter.get_snapshot(project_id)
    assert {n.id for n in snapshot.nodes} == {"p", "d"}
    assert len(snapshot.edges) == 1
    stats = snapshot.stats()
    assert stats["total_nodes"] == 2
    assert stats["total_edges"] == 1
    assert stats["nodes_by_kind"]["Project"] == 1

    rf = snapshot.to_react_flow()
    assert len(rf["nodes"]) == 2
    assert {n["data"]["kind"] for n in rf["nodes"]} == {"Project", "Document"}
    assert rf["edges"][0]["label"] == "HAS_DOCUMENT"

    fetched = await adapter.get_node(project_id, "d")
    assert fetched is not None and fetched.kind == NodeKind.DOCUMENT
    assert await adapter.get_node(project_id, "missing") is None


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_builder_ingestion_and_orchestrator(tmp_path) -> None:
    adapter = InMemoryGraphAdapter(root=str(tmp_path))
    builder = GraphBuilder(project_id="proj_build", adapter=adapter)
    await builder.add_project(name="Build Test", compliance="standard", objective="x")

    counts = await builder.add_documents_from_ingestion(
        {
            "files": [
                {"file": "a.pdf", "parser": "pdf", "chunks": 2},
                {"file": "b.eml", "parser": "email", "chunks": 1},
            ]
        }
    )
    assert counts == {"documents": 2, "chunks": 3}

    artefact_counts = await builder.add_orchestrator_outputs(
        {
            "schedule": {
                "artefacts": [
                    {"kind": "milestone", "value": "Kickoff complete"},
                    {"kind": "task", "value": "Draft scope"},
                ]
            },
            "risk": {
                "artefacts": [
                    {"kind": "risk", "value": "Risk: Vendor delay | ..."}
                ]
            },
            "compliance": {
                "artefacts": [
                    {"kind": "compliance_control", "value": "Control: x | ..."}
                ]
            },
            "contracts": {
                "artefacts": [
                    {"kind": "contract_template", "label": "sow", "value": "..."}
                ]
            },
            "comms": {
                "artefacts": [
                    {"kind": "comms_template", "label": "kickoff_email", "value": "..."}
                ]
            },
        }
    )
    assert artefact_counts["Milestone"] == 1
    assert artefact_counts["Task"] == 1
    assert artefact_counts["Risk"] == 1
    assert artefact_counts["Control"] == 1
    assert artefact_counts["Contract"] == 1
    assert artefact_counts["CommsTemplate"] == 1

    snapshot = await builder.snapshot()
    kinds = {n.kind for n in snapshot.nodes}
    assert {
        NodeKind.PROJECT,
        NodeKind.DOCUMENT,
        NodeKind.CHUNK,
        NodeKind.MILESTONE,
        NodeKind.TASK,
        NodeKind.RISK,
        NodeKind.CONTROL,
        NodeKind.CONTRACT,
        NodeKind.COMMS_TEMPLATE,
    }.issubset(kinds)
    edge_kinds = {e.kind for e in snapshot.edges}
    assert {
        EdgeKind.HAS_DOCUMENT,
        EdgeKind.CONTAINS_CHUNK,
        EdgeKind.GENERATED,
    }.issubset(edge_kinds)


# ---------------------------------------------------------------------------
# End-to-end: project creation populates the graph
# ---------------------------------------------------------------------------
def test_project_creation_populates_graph_endpoints() -> None:
    reset_graph_adapter()
    client = TestClient(app)
    files = [("files", ("kickoff.eml", io.BytesIO(SAMPLE_EMAIL), "message/rfc822"))]
    res = client.post(
        "/api/v1/projects/",
        files=files,
        data={
            "name": "Graph Demo",
            "compliance": "standard",
            "objective": "Build a graph end-to-end",
        },
    )
    assert res.status_code == 200, res.text
    payload = res.json()
    project_id = payload["project_id"]
    assert payload["plan"]["graph_artefacts"], "orchestrator should have produced artefacts"

    res = client.get(f"/api/v1/projects/{project_id}/graph/stats")
    assert res.status_code == 200
    stats = res.json()
    assert stats["project_id"] == project_id
    assert stats["nodes_by_kind"].get("Project") == 1
    assert stats["nodes_by_kind"].get("Document", 0) >= 1
    assert stats["nodes_by_kind"].get("Chunk", 0) >= 1

    res = client.get(f"/api/v1/projects/{project_id}/graph/")
    assert res.status_code == 200
    body = res.json()
    assert any(n["kind"] == "Project" for n in body["nodes"])
    assert any(e["kind"] == "HAS_DOCUMENT" for e in body["edges"])

    res = client.get(f"/api/v1/projects/{project_id}/graph/react-flow")
    assert res.status_code == 200
    rf = res.json()
    sample_node = rf["nodes"][0]
    assert {"id", "type", "position", "data"}.issubset(sample_node)
    assert "x" in sample_node["position"] and "y" in sample_node["position"]


def test_graph_node_404() -> None:
    client = TestClient(app)
    res = client.get("/api/v1/projects/proj_unknown/graph/nodes/n_missing")
    assert res.status_code == 404


def test_graph_schema_endpoint() -> None:
    client = TestClient(app)
    res = client.get("/api/v1/projects/proj_anything/graph/schema")
    assert res.status_code == 200
    body = res.json()
    assert "Project" in body["node_kinds"]
    assert "GENERATED" in body["edge_kinds"]


def test_get_graph_adapter_factory_uses_memory_by_default() -> None:
    reset_graph_adapter()
    adapter = get_graph_adapter()
    assert isinstance(adapter, InMemoryGraphAdapter)
