import re
import zipfile
from pathlib import Path
from typing import BinaryIO
from xml.etree import ElementTree

from ingestion.parsers.base import (
    ParsedChunk,
    ParsedDocument,
    chunk_text,
    normalize_text,
    read_bytes,
    source_hash,
    source_name_for,
)


TEXT_TAGS = {
    "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t",
    "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t",
    "{http://schemas.openxmlformats.org/drawingml/2006/main}t",
}


def parse_office(
    source: str | Path | BinaryIO,
    *,
    filename: str | None = None,
    chunk_size: int = 1800,
    chunk_overlap: int = 200,
) -> ParsedDocument:
    raw = read_bytes(source)
    source_name = source_name_for(source, filename, "uploaded.office")
    digest = source_hash(raw)
    suffix = Path(source_name).suffix.lower()
    warnings: list[str] = []
    text_sections: list[str] = []

    try:
        from io import BytesIO

        with zipfile.ZipFile(BytesIO(raw)) as archive:
            members = _candidate_members(archive.namelist(), suffix)
            for member in members:
                extracted = _extract_xml_text(archive.read(member))
                if extracted:
                    text_sections.append(extracted)
    except zipfile.BadZipFile:
        warnings.append(f"{source_name}: not a valid Office Open XML archive")

    normalized = normalize_text("\n\n".join(text_sections))
    chunks = [
        ParsedChunk(
            source=source_name,
            text=text,
            metadata={
                "parser": "office",
                "source_hash": digest,
                "file_type": suffix.removeprefix("."),
                "chunk_index": index,
                "chunk_size": len(text),
            },
        )
        for index, text in enumerate(
            chunk_text(normalized, chunk_size=chunk_size, chunk_overlap=chunk_overlap) if normalized else [],
            start=1,
        )
    ]

    if not normalized and not warnings:
        warnings.append(f"{source_name}: no extractable Office text found")

    metadata = {
        "parser": "office",
        "source": source_name,
        "source_hash": digest,
        "file_type": suffix.removeprefix("."),
        "chunk_count": len(chunks),
    }
    return ParsedDocument(source=source_name, chunks=chunks, metadata=metadata, warnings=warnings)


def _candidate_members(names: list[str], suffix: str) -> list[str]:
    if suffix == ".docx":
        return [name for name in names if name == "word/document.xml" or name.startswith("word/header")]
    if suffix == ".xlsx":
        return [
            name
            for name in names
            if name == "xl/sharedStrings.xml" or re.match(r"xl/worksheets/sheet\d+\.xml", name)
        ]
    if suffix == ".pptx":
        return [name for name in names if re.match(r"ppt/slides/slide\d+\.xml", name)]
    return [name for name in names if name.endswith(".xml")]


def _extract_xml_text(raw_xml: bytes) -> str:
    try:
        root = ElementTree.fromstring(raw_xml)
    except ElementTree.ParseError:
        return ""

    values = [element.text for element in root.iter() if element.tag in TEXT_TAGS and element.text]
    return " ".join(values)
