"""IFC (BIM) parser (Phase 2).

Extracts project metadata, spatial structure (site/building/storey), and
element inventories from Industry Foundation Classes models. Uses
``ifcopenshell`` when available; otherwise performs a STEP text scan so
basic BIM summaries remain searchable without the native library.
"""

from __future__ import annotations

import io
import logging
import re
from collections import Counter
from typing import Any

from app.ingestion.chunking import ChunkingOptions, chunk_text
from app.ingestion.parsers.common.base import (
    FileLike,
    ParsedDocument,
    ParserResult,
)

logger = logging.getLogger(__name__)

try:  # pragma: no cover - optional
    import ifcopenshell  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    ifcopenshell = None  # type: ignore[assignment]

_IFC_ENTITY_RE = re.compile(r"IFC([A-Z0-9_]+)\(", re.MULTILINE)
_IFC_PROJECT_RE = re.compile(
    r"IFCPROJECT\s*\(\s*'([^']*)'\s*,\s*(?:\$|'[^']*')\s*,\s*'([^']*)'",
    re.IGNORECASE,
)


class IFCParser:
    name = "ifc"
    extensions = (".ifc", ".ifczip")

    def __init__(self, chunking: ChunkingOptions | None = None) -> None:
        self.chunking = chunking or ChunkingOptions()

    async def parse(self, file: FileLike) -> ParserResult:
        data = await file.read()
        result = ParserResult()

        if file.filename.lower().endswith(".ifczip"):
            result.warnings.append(
                "IFCZIP requires ifcopenshell; attempting native open"
            )

        if ifcopenshell is not None:
            try:
                return self._parse_with_ifcopenshell(file.filename, data, result)
            except Exception as exc:
                result.warnings.append(
                    f"ifcopenshell failed for {file.filename}, falling back to text scan: {exc}"
                )

        return self._parse_text_scan(file.filename, data, result)

    def _parse_with_ifcopenshell(
        self, filename: str, data: bytes, result: ParserResult
    ) -> ParserResult:
        model = ifcopenshell.open(io.BytesIO(data))  # type: ignore[union-attr]

        projects = model.by_type("IfcProject")
        project_name = projects[0].Name if projects and projects[0].Name else filename
        schema = getattr(model, "schema", None) or "unknown"

        summary_lines = [
            f"BIM model: {project_name}",
            f"Schema: {schema}",
            f"File: {filename}",
        ]

        spatial = self._spatial_structure(model)
        if spatial:
            summary_lines.append("Spatial structure:")
            summary_lines.extend(f"  - {line}" for line in spatial)

        element_counts = self._element_inventory(model)
        if element_counts:
            summary_lines.append("Element inventory:")
            for kind, count in element_counts[:20]:
                summary_lines.append(f"  - {kind}: {count}")

        result.chunks.append(
            ParsedDocument(
                source=filename,
                text="\n".join(summary_lines),
                metadata={
                    "parser": self.name,
                    "section": "summary",
                    "format": "ifc",
                    "project": project_name,
                    "schema": schema,
                    "element_counts": dict(element_counts),
                    "engine": "ifcopenshell",
                },
            )
        )

        storeys = model.by_type("IfcBuildingStorey")
        for storey in storeys[:50]:
            label = storey.Name or storey.GlobalId
            elements = self._storey_elements(model, storey)
            if not elements:
                continue
            storey_text = f"Storey '{label}': " + ", ".join(
                f"{kind}={count}" for kind, count in elements[:15]
            )
            result.chunks.append(
                ParsedDocument(
                    source=filename,
                    text=storey_text,
                    metadata={
                        "parser": self.name,
                        "section": "storey",
                        "format": "ifc",
                        "storey": label,
                        "element_counts": dict(elements),
                        "engine": "ifcopenshell",
                    },
                )
            )

        property_chunks = self._property_sets(model, filename)
        for chunk in property_chunks:
            result.chunks.append(chunk)

        return result

    def _spatial_structure(self, model: Any) -> list[str]:
        lines: list[str] = []
        for site in model.by_type("IfcSite")[:5]:
            lines.append(f"Site: {site.Name or site.GlobalId}")
        for building in model.by_type("IfcBuilding")[:10]:
            lines.append(f"Building: {building.Name or building.GlobalId}")
        for storey in model.by_type("IfcBuildingStorey")[:30]:
            elevation = getattr(getattr(storey, "Elevation", None), "wrappedValue", None)
            elev_text = f" (elevation {elevation})" if elevation is not None else ""
            lines.append(f"Storey: {storey.Name or storey.GlobalId}{elev_text}")
        return lines

    def _element_inventory(self, model: Any) -> list[tuple[str, int]]:
        counts: Counter[str] = Counter()
        for element in model.by_type("IfcProduct"):
            kind = element.is_a()
            if kind in {"IfcSite", "IfcBuilding", "IfcBuildingStorey", "IfcSpace"}:
                continue
            counts[kind] += 1
        return counts.most_common()

    def _storey_elements(self, model: Any, storey: Any) -> list[tuple[str, int]]:
        counts: Counter[str] = Counter()
        try:
            related = model.get_inverse(storey)
        except Exception:
            return []
        for rel in related:
            if not rel.is_a("IfcRelContainedInSpatialStructure"):
                continue
            for element in rel.RelatedElements:
                counts[element.is_a()] += 1
        return counts.most_common()

    def _property_sets(self, model: Any, filename: str) -> list[ParsedDocument]:
        chunks: list[ParsedDocument] = []
        lines: list[str] = []
        for pset in model.by_type("IfcPropertySet")[:40]:
            name = pset.Name or "PropertySet"
            props: list[str] = []
            for prop in getattr(pset, "HasProperties", []) or []:
                prop_name = getattr(prop, "Name", None)
                if prop_name:
                    props.append(str(prop_name))
            if props:
                lines.append(f"{name}: {', '.join(props[:12])}")
        if not lines:
            return chunks
        text = "Property sets:\n" + "\n".join(lines)
        for index, piece in enumerate(chunk_text(text, self.chunking)):
            chunks.append(
                ParsedDocument(
                    source=filename,
                    text=piece,
                    metadata={
                        "parser": self.name,
                        "section": "properties",
                        "format": "ifc",
                        "chunk_index": index,
                        "engine": "ifcopenshell",
                    },
                )
            )
        return chunks

    def _parse_text_scan(
        self, filename: str, data: bytes, result: ParserResult
    ) -> ParserResult:
        try:
            text = data.decode("utf-8", errors="replace")
        except Exception as exc:
            result.warnings.append(f"Could not decode IFC {filename}: {exc}")
            return result

        entity_counts = Counter(
            f"Ifc{match}" for match in _IFC_ENTITY_RE.findall(text)
        )
        project_match = _IFC_PROJECT_RE.search(text)
        project_name = project_match.group(2) if project_match else filename

        summary_lines = [
            f"BIM model: {project_name}",
            f"File: {filename}",
            f"IFC entities detected: {sum(entity_counts.values())}",
        ]
        if entity_counts:
            top = entity_counts.most_common(20)
            summary_lines.append(
                "Entity breakdown: "
                + ", ".join(f"{kind}={count}" for kind, count in top)
            )

        result.chunks.append(
            ParsedDocument(
                source=filename,
                text="\n".join(summary_lines),
                metadata={
                    "parser": self.name,
                    "section": "summary",
                    "format": "ifc",
                    "project": project_name,
                    "element_counts": dict(entity_counts),
                    "engine": "text_scan",
                },
            )
        )
        if ifcopenshell is None:
            result.warnings.append(
                "ifcopenshell not installed; used lightweight IFC text scan (install ifcopenshell for full BIM parsing)"
            )
        return result
