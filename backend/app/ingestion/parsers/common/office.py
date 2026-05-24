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

NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
    "office": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "word": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "drawing": "http://schemas.openxmlformats.org/drawingml/2006/main",
}

TEXT_TAGS = {
    f"{{{NS['word']}}}t",
    f"{{{NS['main']}}}t",
    f"{{{NS['drawing']}}}t",
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
    table_count = 0

    try:
        from io import BytesIO

        with zipfile.ZipFile(BytesIO(raw)) as archive:
            if suffix == ".xlsx":
                shared_strings = _load_shared_strings(archive)
                sheet_names = _sheet_names(archive)
                for sheet_name, member in sheet_names:
                    rows = _extract_xlsx_rows(archive.read(member), shared_strings)
                    if rows:
                        table_count += 1
                        text_sections.append(_format_table(sheet_name, rows))
            elif suffix == ".docx":
                if "word/document.xml" in archive.namelist():
                    text_sections.append(_extract_docx_text(archive.read("word/document.xml")))
                for member in [name for name in archive.namelist() if name.startswith("word/header")]:
                    extracted = _extract_docx_text(archive.read(member))
                    if extracted:
                        text_sections.append(extracted)
            elif suffix == ".pptx":
                slide_members = sorted(
                    name for name in archive.namelist() if re.match(r"ppt/slides/slide\d+\.xml", name)
                )
                for index, member in enumerate(slide_members, start=1):
                    extracted = _extract_xml_text(archive.read(member))
                    if extracted:
                        text_sections.append(f"Slide {index}: {extracted}")
            else:
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
                "table_count": table_count if suffix == ".xlsx" else None,
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
        "table_count": table_count if suffix == ".xlsx" else 0,
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


def _extract_docx_text(raw_xml: bytes) -> str:
    try:
        root = ElementTree.fromstring(raw_xml)
    except ElementTree.ParseError:
        return ""

    lines: list[str] = []
    body = root.find("word:body", NS)
    if body is None:
        return _extract_xml_text(raw_xml)

    for child in body:
        tag = child.tag.split("}")[-1]
        if tag == "p":
            style = _docx_paragraph_style(child)
            text = _docx_paragraph_text(child)
            if not text:
                continue
            if style and "heading" in style.lower():
                lines.append(f"Heading: {text}")
            else:
                lines.append(text)
        elif tag == "tbl":
            table_lines = _docx_table_text(child)
            if table_lines:
                lines.append("Table:")
                lines.extend(table_lines)

    return "\n".join(lines)


def _docx_paragraph_style(paragraph: ElementTree.Element) -> str | None:
    props = paragraph.find("word:pPr", NS)
    if props is None:
        return None
    style = props.find("word:pStyle", NS)
    if style is None:
        return None
    return style.attrib.get(f"{{{NS['word']}}}val")


def _docx_paragraph_text(paragraph: ElementTree.Element) -> str:
    parts = [node.text for node in paragraph.findall(".//word:t", NS) if node.text]
    return " ".join(parts).strip()


def _docx_table_text(table: ElementTree.Element) -> list[str]:
    rows: list[str] = []
    for row in table.findall(".//word:tr", NS):
        cells = []
        for cell in row.findall("word:tc", NS):
            cell_text = " ".join(node.text for node in cell.findall(".//word:t", NS) if node.text).strip()
            cells.append(cell_text)
        if any(cells):
            rows.append("\t".join(cells))
    return rows


def _load_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    strings: list[str] = []
    for item in root.findall("main:si", NS):
        parts = [node.text or "" for node in item.findall(".//main:t", NS)]
        strings.append("".join(parts))
    return strings


def _sheet_names(archive: zipfile.ZipFile) -> list[tuple[str, str]]:
    workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
    rels = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    rel_map = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in rels.findall("rel:Relationship", NS)
    }
    sheets: list[tuple[str, str]] = []
    for sheet in workbook.findall("main:sheets/main:sheet", NS):
        name = sheet.attrib.get("name", "Sheet")
        rel_id = sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
        target = rel_map.get(rel_id or "")
        if not target:
            continue
        member = target if target.startswith("xl/") else f"xl/{target.lstrip('/')}"
        if member in archive.namelist():
            sheets.append((name, member))
    return sheets


def _extract_xlsx_rows(raw_xml: bytes, shared_strings: list[str]) -> list[list[str]]:
    try:
        root = ElementTree.fromstring(raw_xml)
    except ElementTree.ParseError:
        return []

    rows: list[list[str]] = []
    for row in root.findall("main:sheetData/main:row", NS):
        values: list[str] = []
        for cell in row.findall("main:c", NS):
            values.append(_cell_value(cell, shared_strings))
        if any(value.strip() for value in values):
            rows.append(values)
    return rows


def _cell_value(cell: ElementTree.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    inline = cell.find("main:is", NS)
    if inline is not None:
        parts = [node.text or "" for node in inline.findall(".//main:t", NS)]
        return "".join(parts)

    value_node = cell.find("main:v", NS)
    if value_node is None or value_node.text is None:
        return ""

    if cell_type == "s":
        try:
            return shared_strings[int(value_node.text)]
        except (IndexError, ValueError):
            return value_node.text
    return value_node.text


def _format_table(sheet_name: str, rows: list[list[str]]) -> str:
    lines = [f"Sheet: {sheet_name}"]
    for row in rows:
        lines.append("\t".join(row))
    return "\n".join(lines)
