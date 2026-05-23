import mailbox
import tempfile
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


def _message_text(message) -> str:
    text_parts: list[str] = []
    for part in message.walk():
        content_disposition = part.get_content_disposition()
        content_type = part.get_content_type()
        part_filename = part.get_filename()

        if content_disposition == "attachment" or part_filename:
            continue

        if content_type == "text/plain":
            text_parts.append(str(part.get_content()))
        elif content_type == "text/html" and not text_parts:
            text_parts.append(str(part.get_content()))

    return normalize_text("\n\n".join(text_parts))


def parse_mbox(
    source: str | Path | BinaryIO,
    *,
    filename: str | None = None,
    chunk_size: int = 1800,
    chunk_overlap: int = 200,
) -> ParsedDocument:
    raw = read_bytes(source)
    source_name = source_name_for(source, filename, "uploaded.mbox")
    digest = source_hash(raw)
    warnings: list[str] = []

    with tempfile.TemporaryDirectory() as temp_dir:
        mbox_path = Path(temp_dir) / "archive.mbox"
        mbox_path.write_bytes(raw)
        archive = mailbox.mbox(str(mbox_path))

        chunks: list[ParsedChunk] = []
        message_count = 0
        for index, message in enumerate(archive, start=1):
            message_count += 1
            if message is None:
                warnings.append(f"{source_name}: skipped empty message at index {index}")
                continue

            if hasattr(message, "as_bytes"):
                parsed_message = BytesParser(policy=policy.default).parsebytes(message.as_bytes())
            else:
                parsed_message = message

            normalized = _message_text(parsed_message)
            subject = parsed_message.get("Subject")
            sender = parsed_message.get("From")
            message_id = parsed_message.get("Message-ID")

            for chunk_index, text in enumerate(
                chunk_text(normalized, chunk_size=chunk_size, chunk_overlap=chunk_overlap) if normalized else [],
                start=1,
            ):
                chunks.append(
                    ParsedChunk(
                        source=f"{source_name}#message-{index}",
                        text=text,
                        metadata={
                            "parser": "mbox",
                            "source_hash": digest,
                            "archive": source_name,
                            "message_index": index,
                            "message_id": message_id,
                            "subject": subject,
                            "from": sender,
                            "to": parsed_message.get("To"),
                            "date": parsed_message.get("Date"),
                            "chunk_index": chunk_index,
                            "chunk_size": len(text),
                        },
                    )
                )

            if not normalized:
                warnings.append(f"{source_name} message {index}: no text body found")

        archive.close()

    metadata = {
        "parser": "mbox",
        "source": source_name,
        "source_hash": digest,
        "message_count": message_count,
        "chunk_count": len(chunks),
    }
    if message_count == 0:
        warnings.append(f"{source_name}: mailbox archive contains no messages")

    return ParsedDocument(source=source_name, chunks=chunks, metadata=metadata, warnings=warnings)
