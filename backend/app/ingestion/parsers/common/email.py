from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import BinaryIO

from ingestion.parsers.base import (
    ParsedChunk,
    ParsedDocument,
    chunk_text,
    normalize_text,
    read_bytes,
    source_hash,
    source_name_for,
)


def parse_email(
    source: str | Path | BinaryIO,
    *,
    filename: str | None = None,
    chunk_size: int = 1800,
    chunk_overlap: int = 200,
) -> ParsedDocument:
    raw = read_bytes(source)
    source_name = source_name_for(source, filename, "uploaded.eml")
    digest = source_hash(raw)
    message = BytesParser(policy=policy.default).parsebytes(raw)
    warnings: list[str] = []

    text_parts: list[str] = []
    attachments: list[dict] = []
    for part in message.walk():
        content_disposition = part.get_content_disposition()
        content_type = part.get_content_type()
        part_filename = part.get_filename()

        if content_disposition == "attachment" or part_filename:
            attachments.append(
                {
                    "filename": part_filename,
                    "content_type": content_type,
                    "size": len(part.get_payload(decode=True) or b""),
                }
            )
            continue

        if content_type == "text/plain":
            text_parts.append(str(part.get_content()))
        elif content_type == "text/html" and not text_parts:
            text_parts.append(str(part.get_content()))

    normalized = normalize_text("\n\n".join(text_parts))
    chunks = [
        ParsedChunk(
            source=source_name,
            text=text,
            metadata={
                "parser": "email",
                "source_hash": digest,
                "message_id": message.get("Message-ID"),
                "subject": message.get("Subject"),
                "from": message.get("From"),
                "to": message.get("To"),
                "date": message.get("Date"),
                "attachment_count": len(attachments),
                "chunk_index": index,
                "chunk_size": len(text),
            },
        )
        for index, text in enumerate(
            chunk_text(normalized, chunk_size=chunk_size, chunk_overlap=chunk_overlap) if normalized else [],
            start=1,
        )
    ]

    if not normalized:
        warnings.append(f"{source_name}: no text body found")

    metadata = {
        "parser": "email",
        "source": source_name,
        "source_hash": digest,
        "subject": message.get("Subject"),
        "from": message.get("From"),
        "to": message.get("To"),
        "date": message.get("Date"),
        "message_id": message.get("Message-ID"),
        "attachment_count": len(attachments),
        "attachments": attachments,
        "chunk_count": len(chunks),
    }
    return ParsedDocument(source=source_name, chunks=chunks, metadata=metadata, warnings=warnings)
