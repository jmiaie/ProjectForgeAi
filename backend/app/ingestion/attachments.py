from io import BytesIO
from pathlib import Path

from ingestion.parsers.base import ParsedDocument


def parse_attachment(
    filename: str | None,
    payload: bytes,
    *,
    parent_source: str,
) -> ParsedDocument | None:
    if not payload:
        return None

    attachment_name = filename or "attachment.bin"
    suffix = Path(attachment_name).suffix.lower()
    parser = _parser_for_suffix(suffix)
    if parser is None:
        return ParsedDocument(
            source=f"{parent_source}::{attachment_name}",
            chunks=[],
            metadata={
                "parser": "attachment",
                "source": attachment_name,
                "parent_source": parent_source,
                "chunk_count": 0,
                "unsupported_suffix": suffix or "unknown",
            },
            warnings=[f"{attachment_name}: attachment type {suffix or 'unknown'} is not supported"],
        )

    parsed = parser(BytesIO(payload), filename=attachment_name)
    metadata = {
        **parsed.metadata,
        "parser": "attachment",
        "parent_source": parent_source,
        "attachment_name": attachment_name,
    }
    chunks = []
    for chunk in parsed.chunks:
        chunk_metadata = {**chunk.metadata, "parent_source": parent_source, "attachment_name": attachment_name}
        chunks.append(chunk.__class__(source=chunk.source, text=chunk.text, metadata=chunk_metadata))

    return ParsedDocument(
        source=f"{parent_source}::{attachment_name}",
        chunks=chunks,
        metadata=metadata,
        warnings=[*parsed.warnings],
    )


def _parser_for_suffix(suffix: str):
    if suffix == ".pdf":
        from ingestion.parsers.common.pdf import parse_pdf

        return parse_pdf
    if suffix in {".docx", ".xlsx", ".pptx"}:
        from ingestion.parsers.common.office import parse_office

        return parse_office
    if suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".tif", ".tiff", ".bmp"}:
        from ingestion.parsers.common.image import parse_image

        return parse_image
    if suffix == ".eml":
        from ingestion.parsers.common.email import parse_email

        return parse_email
    return None
