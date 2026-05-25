import mailbox
import tempfile
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

from ingestion.parsers.common.email import parse_email
from ingestion.parsers.base import ParsedChunk, ParsedDocument, read_bytes, source_hash, source_name_for


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
    chunks: list[ParsedChunk] = []
    message_count = 0

    with tempfile.TemporaryDirectory() as temp_dir:
        mbox_path = Path(temp_dir) / "archive.mbox"
        mbox_path.write_bytes(raw)
        archive = mailbox.mbox(str(mbox_path))

        for index, message in enumerate(archive, start=1):
            message_count += 1
            if message is None:
                warnings.append(f"{source_name}: skipped empty message at index {index}")
                continue

            raw_message = message.as_bytes() if hasattr(message, "as_bytes") else bytes(message)
            parsed_message = parse_email(
                BytesIO(raw_message),
                filename=f"{source_name}#message-{index}.eml",
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
            warnings.extend(parsed_message.warnings)
            for chunk in parsed_message.chunks:
                metadata = {
                    **chunk.metadata,
                    "archive": source_name,
                    "message_index": index,
                    "source_hash": digest,
                }
                chunks.append(
                    ParsedChunk(
                        source=f"{source_name}#message-{index}",
                        text=chunk.text,
                        metadata=metadata,
                    )
                )

        archive.close()

    metadata = {
        "parser": "mbox",
        "source": source_name,
        "source_hash": digest,
        "message_count": message_count,
        "chunk_count": len(chunks),
        "attachment_chunks_indexed": sum(
            1 for chunk in chunks if chunk.metadata.get("attachment_name")
        ),
    }
    if message_count == 0:
        warnings.append(f"{source_name}: mailbox archive contains no messages")

    return ParsedDocument(source=source_name, chunks=chunks, metadata=metadata, warnings=warnings)
