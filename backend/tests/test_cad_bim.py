"""Tests for Phase 2 CAD/BIM parsers."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.ingestion.parsers.cad import DXFParser, IFCParser
from app.ingestion.pipeline import IngestionPipeline


@dataclass
class FakeUpload:
    filename: str
    payload: bytes

    async def read(self) -> bytes:
        return self.payload


MINIMAL_DXF = b"""  0
SECTION
  2
HEADER
  9
$ACADVER
  1
AC1015
  0
ENDSEC
  0
SECTION
  2
ENTITIES
  0
LINE
  8
Walls
  0
LINE
  8
Walls
  0
TEXT
  8
Notes
  1
Lobby ceiling height 3.2m
  0
CIRCLE
  8
Fixtures
  0
ENDSEC
  0
EOF
"""

MINIMAL_IFC = b"""ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('ViewDefinition [CoordinationView]'),'2;1');
FILE_NAME('sample.ifc','2025-01-01',('ProjectForge'),('ProjectForge'),'','','');
FILE_SCHEMA(('IFC4'));
ENDSEC;
DATA;
#1=IFCPROJECT('0ProjectGuid',$,'Riverside Tower',$,$,$,$,(#2),#3);
#2=IFCGEOMETRICREPRESENTATIONCONTEXT($,'Model',3,1.E-05,#4,$);
#3=IFCUNITASSIGNMENT((#5));
#4=IFCCARTESIANPOINT((0.,0.,0.));
#5=IFCSIUNIT(*,.LENGTHUNIT.,$,.METRE.);
#10=IFCBUILDING('0BuildingGuid',$,'Tower A',$,$,#1,$,$,.ELEMENT.,$,$,$);
#11=IFCBUILDINGSTOREY('0StoreyGuid',$,'Level 01',$,$,#10,$,$,.ELEMENT.,0.);
#20=IFCWALL('0WallGuid',$,'Exterior Wall',$,$,#11,$,$);
#21=IFCWALL('0WallGuid2',$,'Interior Wall',$,$,#11,$,$);
#22=IFCDOOR('0DoorGuid',$,'Entry Door',$,$,#11,$,$);
ENDSEC;
END-ISO-10303-21;
"""


@pytest.mark.asyncio
async def test_dxf_parser_text_scan_extracts_layers_and_entities() -> None:
    parser = DXFParser()
    result = await parser.parse(FakeUpload(filename="floor.dxf", payload=MINIMAL_DXF))

    assert result.chunks
    summary = result.chunks[0]
    assert summary.metadata["section"] == "summary"
    assert summary.metadata["format"] == "dxf"
    assert "Walls" in summary.metadata["layers"]
    assert summary.metadata["entity_counts"].get("LINE") == 2
    assert "Walls" in summary.text or "LINE" in summary.text


@pytest.mark.asyncio
async def test_ifc_parser_text_scan_extracts_project_and_entities() -> None:
    parser = IFCParser()
    result = await parser.parse(FakeUpload(filename="tower.ifc", payload=MINIMAL_IFC))

    assert result.chunks
    summary = result.chunks[0]
    assert summary.metadata["section"] == "summary"
    assert summary.metadata["format"] == "ifc"
    assert summary.metadata["project"] == "Riverside Tower"
    assert summary.metadata["element_counts"].get("IfcWALL") == 2
    assert summary.metadata["element_counts"].get("IfcDOOR") == 1


@pytest.mark.asyncio
async def test_pipeline_routes_cad_and_bim_files(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LOCUS_ROOT", str(tmp_path / "locus"))
    monkeypatch.setenv("OMPA_VAULT_ROOT", str(tmp_path / "vaults"))

    from app.core.config import get_settings

    get_settings.cache_clear()  # type: ignore[attr-defined]

    pipeline = IngestionPipeline()
    summary = await pipeline.process_files(
        project_id="cad-demo",
        files=[
            FakeUpload(filename="floor.dxf", payload=MINIMAL_DXF),
            FakeUpload(filename="tower.ifc", payload=MINIMAL_IFC),
        ],
    )

    assert summary["status"] == "ingested"
    assert summary["total_files"] == 2
    assert summary["total_chunks"] >= 2
    parsers = {entry["parser"] for entry in summary["files"]}
    assert parsers == {"dxf", "ifc"}


@pytest.mark.asyncio
async def test_dxf_parser_with_ezdxf_when_available() -> None:
    ezdxf = pytest.importorskip("ezdxf")

    import io

    doc = ezdxf.new()
    msp = doc.modelspace()
    msp.add_line((0, 0), (10, 0), dxfattribs={"layer": "Structure"})
    msp.add_text("Grid A-1", dxfattribs={"layer": "Annotations", "height": 0.25})

    buffer = io.StringIO()
    doc.write(buffer)
    payload = buffer.getvalue().encode("utf-8")

    parser = DXFParser()
    result = await parser.parse(FakeUpload(filename="generated.dxf", payload=payload))

    assert result.chunks
    assert result.chunks[0].metadata.get("engine") == "ezdxf"
    assert "Structure" in result.chunks[0].metadata.get("layers", [])
    assert any(
        chunk.metadata.get("section") == "annotation"
        for chunk in result.chunks
    )
