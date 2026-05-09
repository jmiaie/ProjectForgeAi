"""Tests for the hardened PDF parser."""

from __future__ import annotations

import io
from dataclasses import dataclass

import pytest

from app.ingestion.chunking import ChunkingOptions
from app.ingestion.parsers.common.pdf import PDFParser

reportlab = pytest.importorskip("reportlab")
from reportlab.lib.pagesizes import LETTER  # noqa: E402
from reportlab.pdfgen import canvas  # noqa: E402
from reportlab.platypus import (  # noqa: E402
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.styles import getSampleStyleSheet  # noqa: E402


@dataclass
class FakeUpload:
    filename: str
    payload: bytes

    async def read(self) -> bytes:
        return self.payload


def _build_text_pdf(pages: int = 2, paragraphs_per_page: int = 4) -> bytes:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=LETTER)
    width, height = LETTER
    for page_index in range(pages):
        text_object = pdf.beginText(72, height - 72)
        text_object.setFont("Helvetica", 11)
        text_object.textLine(f"Page {page_index + 1} heading")
        for para in range(paragraphs_per_page):
            text_object.textLine("")
            text_object.textLine(
                f"Paragraph {para + 1} on page {page_index + 1}: "
                "ProjectForge AI accelerates planning by routing every "
                "document into a living project graph and orchestrating "
                "specialist agents on top of it."
            )
        pdf.drawText(text_object)
        pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def _build_table_pdf() -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER)
    styles = getSampleStyleSheet()
    rows = [
        ["Risk", "Likelihood", "Impact", "Owner"],
        ["Vendor delay", "Medium", "High", "PM"],
        ["Scope creep", "High", "Medium", "Sponsor"],
        ["Budget overrun", "Low", "High", "Finance"],
    ]
    table = Table(rows)
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ]
        )
    )
    doc.build(
        [
            Paragraph("Risk Register", styles["Heading1"]),
            Spacer(1, 12),
            table,
        ]
    )
    return buffer.getvalue()


def _build_empty_pdf() -> bytes:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=LETTER)
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_pdf_parser_extracts_pages_with_metadata() -> None:
    pdf_bytes = _build_text_pdf(pages=2, paragraphs_per_page=3)
    upload = FakeUpload(filename="text.pdf", payload=pdf_bytes)
    parser = PDFParser(
        chunking=ChunkingOptions(chunk_size=400, overlap=40, min_chunk_size=50),
        enable_tables=False,
        enable_ocr_fallback=False,
    )
    result = await parser.parse(upload)

    page_chunks = [c for c in result.chunks if c.metadata.get("section") == "page"]
    assert page_chunks, "should produce at least one page chunk"
    pages_seen = {c.metadata["page"] for c in page_chunks}
    assert pages_seen == {1, 2}
    sample = page_chunks[0]
    assert sample.metadata["total_pages"] == 2
    assert sample.metadata["chunk_count"] >= 1
    assert sample.metadata["width"] and sample.metadata["height"]
    assert "Paragraph" in sample.text or "ProjectForge" in sample.text


@pytest.mark.asyncio
async def test_pdf_parser_chunks_long_pages() -> None:
    pdf_bytes = _build_text_pdf(pages=1, paragraphs_per_page=15)
    upload = FakeUpload(filename="long.pdf", payload=pdf_bytes)
    parser = PDFParser(
        chunking=ChunkingOptions(chunk_size=300, overlap=30, min_chunk_size=50),
        enable_tables=False,
        enable_ocr_fallback=False,
    )
    result = await parser.parse(upload)
    page_chunks = [c for c in result.chunks if c.metadata.get("section") == "page"]
    chunk_counts = {c.metadata["chunk_count"] for c in page_chunks}
    assert chunk_counts and max(chunk_counts) >= 2, (
        "long page should produce multiple chunks"
    )


@pytest.mark.asyncio
async def test_pdf_parser_extracts_tables() -> None:
    pdfplumber = pytest.importorskip("pdfplumber")  # noqa: F841
    pdf_bytes = _build_table_pdf()
    upload = FakeUpload(filename="table.pdf", payload=pdf_bytes)
    parser = PDFParser(
        chunking=ChunkingOptions(chunk_size=2000, overlap=50, min_chunk_size=10),
        enable_tables=True,
        enable_ocr_fallback=False,
    )
    result = await parser.parse(upload)
    table_chunks = [c for c in result.chunks if c.metadata.get("section") == "table"]
    assert table_chunks, "table extraction should yield at least one chunk"
    table = table_chunks[0]
    assert table.metadata["row_count"] >= 4
    assert table.metadata["column_count"] >= 4
    assert "Vendor delay" in table.text
    assert "|" in table.text


@pytest.mark.asyncio
async def test_pdf_parser_empty_pages_produce_no_chunks_without_ocr_deps() -> None:
    pdf_bytes = _build_empty_pdf()
    upload = FakeUpload(filename="empty.pdf", payload=pdf_bytes)
    parser = PDFParser(
        enable_tables=False,
        enable_ocr_fallback=False,
    )
    result = await parser.parse(upload)
    assert all(c.metadata.get("section") != "page" for c in result.chunks)


@pytest.mark.asyncio
async def test_pdf_parser_handles_corrupt_input() -> None:
    upload = FakeUpload(filename="bad.pdf", payload=b"not a real pdf")
    parser = PDFParser(enable_tables=False, enable_ocr_fallback=False)
    result = await parser.parse(upload)
    assert any("Could not open" in w for w in result.warnings)
    assert result.chunks == []


@pytest.mark.asyncio
async def test_pdf_parser_ocr_fallback_invoked_when_text_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """If a page returns empty text, the OCR fallback path should be called."""

    pdf_bytes = _build_empty_pdf()
    upload = FakeUpload(filename="empty.pdf", payload=pdf_bytes)
    parser = PDFParser(enable_tables=False, enable_ocr_fallback=True)

    captured: dict[str, int] = {"calls": 0}

    def fake_ocr(self, file, data, index, result, page_meta):  # type: ignore[no-untyped-def]
        captured["calls"] += 1
        return "OCR-RECOVERED-TEXT for page %d" % (index + 1)

    monkeypatch.setattr(PDFParser, "_ocr_page", fake_ocr)
    result = await parser.parse(upload)

    assert captured["calls"] >= 1
    page_chunks = [c for c in result.chunks if c.metadata.get("section") == "page"]
    assert page_chunks
    assert "OCR-RECOVERED-TEXT" in page_chunks[0].text
    assert page_chunks[0].metadata.get("ocr") is True
