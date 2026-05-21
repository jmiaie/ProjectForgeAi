"""DXF (CAD) parser (Phase 2).

Extracts layer inventories, entity summaries, and text annotations from
AutoCAD DXF drawings. Uses ``ezdxf`` when available; otherwise falls back
to a lightweight text scan of the ENTITIES section so operators still get
searchable metadata without the optional dependency.
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
    import ezdxf  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    ezdxf = None  # type: ignore[assignment]


_LAYER_RE = re.compile(r"^\s*8\s*\n\s*(.+?)\s*$", re.MULTILINE)
_ENTITY_RE = re.compile(r"^\s*0\s*\n\s*([A-Z_0-9]+)\s*$", re.MULTILINE)


class DXFParser:
    name = "dxf"
    extensions = (".dxf",)

    def __init__(self, chunking: ChunkingOptions | None = None) -> None:
        self.chunking = chunking or ChunkingOptions()

    async def parse(self, file: FileLike) -> ParserResult:
        data = await file.read()
        result = ParserResult()

        if ezdxf is not None:
            try:
                return self._parse_with_ezdxf(file.filename, data, result)
            except Exception as exc:
                result.warnings.append(
                    f"ezdxf failed for {file.filename}, falling back to text scan: {exc}"
                )

        return self._parse_text_scan(file.filename, data, result)

    def _parse_with_ezdxf(
        self, filename: str, data: bytes, result: ParserResult
    ) -> ParserResult:
        stream = io.BytesIO(data)
        try:
            doc = ezdxf.read(stream)  # type: ignore[union-attr]
        except Exception:
            text = data.decode("utf-8", errors="replace")
            doc = ezdxf.read(io.StringIO(text))  # type: ignore[union-attr]
        msp = doc.modelspace()

        layer_names = sorted({layer.dxf.name for layer in doc.layers})
        entity_counts: Counter[str] = Counter()
        text_annotations: list[str] = []
        used_layers: set[str] = set(layer_names)

        for entity in msp:
            entity_type = entity.dxftype()
            entity_counts[entity_type] += 1
            layer = getattr(entity.dxf, "layer", None)
            if layer:
                used_layers.add(layer)
            if entity_type in {"TEXT", "MTEXT"}:
                text = getattr(entity.dxf, "text", "") or ""
                if text.strip():
                    text_annotations.append(text.strip())

        layer_names = sorted(used_layers)

        summary_lines = [
            f"DXF drawing: {filename}",
            f"Layers ({len(layer_names)}): {', '.join(layer_names[:40])}",
            f"Model-space entities: {sum(entity_counts.values())}",
        ]
        if entity_counts:
            top_entities = entity_counts.most_common(12)
            summary_lines.append(
                "Entity breakdown: "
                + ", ".join(f"{kind}={count}" for kind, count in top_entities)
            )

        result.chunks.append(
            ParsedDocument(
                source=filename,
                text="\n".join(summary_lines),
                metadata={
                    "parser": self.name,
                    "section": "summary",
                    "format": "dxf",
                    "layers": layer_names,
                    "entity_counts": dict(entity_counts),
                    "engine": "ezdxf",
                },
            )
        )

        if text_annotations:
            annotation_text = "\n".join(text_annotations)
            for index, piece in enumerate(chunk_text(annotation_text, self.chunking)):
                result.chunks.append(
                    ParsedDocument(
                        source=filename,
                        text=piece,
                        metadata={
                            "parser": self.name,
                            "section": "annotation",
                            "format": "dxf",
                            "chunk_index": index,
                            "engine": "ezdxf",
                        },
                    )
                )

        return result

    def _parse_text_scan(
        self, filename: str, data: bytes, result: ParserResult
    ) -> ParserResult:
        try:
            text = data.decode("utf-8", errors="replace")
        except Exception as exc:
            result.warnings.append(f"Could not decode DXF {filename}: {exc}")
            return result

        if "ENTITIES" not in text:
            result.warnings.append(
                "ezdxf not installed and no ENTITIES section found; indexed metadata only"
            )

        entities_section = text.split("ENTITIES", 1)[-1].split("ENDSEC", 1)[0]
        layers = _LAYER_RE.findall(entities_section)
        layer_counts = Counter(layers)
        entity_types = _ENTITY_RE.findall(entities_section)
        entity_counts = Counter(entity_types)

        summary_lines = [
            f"DXF drawing: {filename}",
            f"Layers detected: {len(layer_counts)}",
        ]
        if layer_counts:
            top_layers = layer_counts.most_common(20)
            summary_lines.append(
                "Layer usage: "
                + ", ".join(f"{name}={count}" for name, count in top_layers)
            )
        if entity_counts:
            top_entities = entity_counts.most_common(12)
            summary_lines.append(
                "Entity breakdown: "
                + ", ".join(f"{kind}={count}" for kind, count in top_entities)
            )

        result.chunks.append(
            ParsedDocument(
                source=filename,
                text="\n".join(summary_lines),
                metadata={
                    "parser": self.name,
                    "section": "summary",
                    "format": "dxf",
                    "layers": sorted(layer_counts.keys()),
                    "entity_counts": dict(entity_counts),
                    "engine": "text_scan",
                },
            )
        )
        if ezdxf is None:
            result.warnings.append(
                "ezdxf not installed; used lightweight DXF text scan (install ezdxf for full parsing)"
            )
        return result
