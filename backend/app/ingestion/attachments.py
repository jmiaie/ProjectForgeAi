from io import BytesIO
from pathlib import Path

from ingestion.parsers.base import ParsedDocument

MAX_ATTACHMENT_DEPTH = 3


def parse_attachment(
    filename: str | None,
    payload: bytes,
    *,
    parent_source: str,
    depth: int = 0,
) -> ParsedDocument | None:
    if not payload:
        return None
    if depth >= MAX_ATTACHMENT_DEPTH:
        return ParsedDocument(
            source=f"{parent_source}::{filename or 'attachment.bin'}",
            chunks=[],
            metadata={
                "parser": "attachment",
                "parent_source": parent_source,
                "depth": depth,
                "chunk_count": 0,
            },
            warnings=[f"{filename or 'attachment'}: nested attachment depth limit reached"],
        )

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
                "depth": depth,
                "chunk_count": 0,
                "unsupported_suffix": suffix or "unknown",
            },
            warnings=[f"{attachment_name}: attachment type {suffix or 'unknown'} is not supported"],
        )

    parsed = parser(BytesIO(payload), filename=attachment_name)
    nested_chunks = list(parsed.chunks)
    nested_warnings = list(parsed.warnings)

    if suffix == ".eml":
        for part in _email_attachment_parts(payload):
            nested = parse_attachment(
                part["filename"],
                part["payload"],
                parent_source=f"{parent_source}::{attachment_name}",
                depth=depth + 1,
            )
            if nested is not None:
                nested_chunks.extend(nested.chunks)
                nested_warnings.extend(nested.warnings)

    metadata = {
        **parsed.metadata,
        "parser": "attachment",
        "parent_source": parent_source,
        "attachment_name": attachment_name,
        "depth": depth,
    }
    chunks = []
    for chunk in nested_chunks:
        chunk_metadata = {
            **chunk.metadata,
            "parent_source": parent_source,
            "attachment_name": attachment_name,
            "depth": depth,
        }
        chunks.append(chunk.__class__(source=chunk.source, text=chunk.text, metadata=chunk_metadata))

    return ParsedDocument(
        source=f"{parent_source}::{attachment_name}",
        chunks=chunks,
        metadata=metadata,
        warnings=nested_warnings,
    )


def _email_attachment_parts(payload: bytes) -> list[dict]:
    from email import policy
    from email.parser import BytesParser

    message = BytesParser(policy=policy.default).parsebytes(payload)
    parts: list[dict] = []
    for part in message.walk():
        part_filename = part.get_filename()
        content_disposition = part.get_content_disposition()
        if not (content_disposition == "attachment" or part_filename):
            continue
        parts.append(
            {
                "filename": part_filename,
                "payload": part.get_payload(decode=True) or b"",
            }
        )
    return parts


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
