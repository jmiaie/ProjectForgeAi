"""Phase 1 parsers: PDFs, images and email."""

from app.ingestion.parsers.common.base import ParsedDocument, ParserResult
from app.ingestion.parsers.common.email import EmailParser
from app.ingestion.parsers.common.image import ImageParser
from app.ingestion.parsers.common.pdf import PDFParser

__all__ = [
    "EmailParser",
    "ImageParser",
    "PDFParser",
    "ParsedDocument",
    "ParserResult",
]
