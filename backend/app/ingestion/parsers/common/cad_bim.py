import re
from pathlib import Path
from typing import BinaryIO

from ingestion.parsers.base import (
    ParsedChunk,
    ParsedDocument,
    normalize_text,
    read_bytes,
    source_hash,
    source_name_for,
)

IFC_ENTITY_PATTERN = re.compile(r"#\d+\s*=\s*([A-Z0-9_]+)\s*\(", re.IGNORECASE)
IFC_SCHEMA_PATTERN = re.compile(r"FILE_SCHEMA\s*\(\s*\(\s*'([^']+)'", re.IGNORECASE)


def parse_ifc(
    source: str | Path | BinaryIO,
    *,
    filename: str | None = None,
) -> ParsedDocument:
    raw = read_bytes(source)
    source_name = source_name_for(source, filename, "model.ifc")
    digest = source_hash(raw)
    warnings: list[str] = []

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1", errors="replace")
        warnings.append(f"{source_name}: IFC decoded with latin-1 fallback")

    schema_match = IFC_SCHEMA_PATTERN.search(text)
    schema = schema_match.group(1) if schema_match else "unknown"
    entities = IFC_ENTITY_PATTERN.findall(text)
    entity_counts: dict[str, int] = {}
    for entity in entities:
        entity_counts[entity.upper()] = entity_counts.get(entity.upper(), 0) + 1

    top_entities = sorted(entity_counts.items(), key=lambda item: item[1], reverse=True)[:12]
    summary_lines = [
        f"IFC schema: {schema}",
        f"Entity instances: {len(entities)}",
        f"Distinct entity types: {len(entity_counts)}",
    ]
    if top_entities:
        summary_lines.append("Top entity types:")
        summary_lines.extend(f"- {name}: {count}" for name, count in top_entities)

    summary = normalize_text("\n".join(summary_lines))
    chunks = [
        ParsedChunk(
            source=source_name,
            text=summary,
            metadata={
                "parser": "cad_bim_ifc",
                "source": source_name,
                "source_hash": digest,
                "file_type": "ifc",
                "schema": schema,
                "entity_count": len(entities),
                "entity_types": len(entity_counts),
                "chunk_index": 1,
            },
        )
    ]

    if not entities:
        warnings.append(f"{source_name}: no IFC entities detected (stub metadata-only parse)")

    return ParsedDocument(
        source=source_name,
        chunks=chunks,
        metadata={
            "parser": "cad_bim_ifc",
            "source": source_name,
            "source_hash": digest,
            "file_type": "ifc",
            "schema": schema,
            "chunk_count": len(chunks),
            "entity_count": len(entities),
        },
        warnings=warnings,
    )


def parse_dwg(
    source: str | Path | BinaryIO,
    *,
    filename: str | None = None,
) -> ParsedDocument:
    raw = read_bytes(source)
    source_name = source_name_for(source, filename, "drawing.dwg")
    digest = source_hash(raw)
    warnings = [
        f"{source_name}: DWG parsing is metadata-only; full geometry extraction requires a CAD SDK"
    ]

    header = raw[:6].decode("ascii", errors="replace")
    version_hint = "unknown"
    if header.startswith("AC"):
        version_hint = header
    elif raw[:4] == b"AC10":
        version_hint = raw[:6].decode("ascii", errors="replace")

    summary = normalize_text(
        "\n".join(
            [
                f"DWG drawing: {source_name}",
                f"File size bytes: {len(raw)}",
                f"Version hint: {version_hint}",
                "Geometry and layer extraction pending CAD/BIM adapter integration.",
            ]
        )
    )
    chunks = [
        ParsedChunk(
            source=source_name,
            text=summary,
            metadata={
                "parser": "cad_bim_dwg",
                "source": source_name,
                "source_hash": digest,
                "file_type": "dwg",
                "byte_size": len(raw),
                "version_hint": version_hint,
                "chunk_index": 1,
            },
        )
    ]

    return ParsedDocument(
        source=source_name,
        chunks=chunks,
        metadata={
            "parser": "cad_bim_dwg",
            "source": source_name,
            "source_hash": digest,
            "file_type": "dwg",
            "chunk_count": len(chunks),
            "byte_size": len(raw),
        },
        warnings=warnings,
    )
