"""Email parser (Phase 1).

Handles ``.eml``/``.msg`` style RFC 822 messages using the stdlib
:mod:`email` package, splitting headers, body and attachments into separate
chunks so retrieval can cite each independently.
"""

from __future__ import annotations

from email import policy
from email.parser import BytesParser

from app.ingestion.parsers.common.base import FileLike, ParsedDocument, ParserResult


class EmailParser:
    name = "email"
    extensions = (".eml", ".msg")

    async def parse(self, file: FileLike) -> ParserResult:
        data = await file.read()
        result = ParserResult()

        try:
            msg = BytesParser(policy=policy.default).parsebytes(data)
        except Exception as exc:
            result.warnings.append(f"Could not parse email {file.filename}: {exc}")
            return result

        headers = {
            "from": str(msg.get("From", "")),
            "to": str(msg.get("To", "")),
            "cc": str(msg.get("Cc", "")),
            "subject": str(msg.get("Subject", "")),
            "date": str(msg.get("Date", "")),
        }

        body_parts: list[str] = []
        attachments: list[dict[str, str]] = []

        if msg.is_multipart():
            for part in msg.walk():
                content_disposition = part.get("Content-Disposition", "")
                if "attachment" in content_disposition:
                    attachments.append(
                        {
                            "filename": part.get_filename() or "",
                            "content_type": part.get_content_type(),
                        }
                    )
                    continue
                if part.get_content_type() == "text/plain":
                    payload = part.get_content()
                    if isinstance(payload, str):
                        body_parts.append(payload)
        else:
            payload = msg.get_content()
            if isinstance(payload, str):
                body_parts.append(payload)

        body = "\n\n".join(part for part in body_parts if part).strip()
        header_blob = "\n".join(f"{key.title()}: {value}" for key, value in headers.items() if value)

        if header_blob:
            result.chunks.append(
                ParsedDocument(
                    source=file.filename,
                    text=header_blob,
                    metadata={"parser": self.name, "section": "headers", **headers},
                )
            )
        if body:
            result.chunks.append(
                ParsedDocument(
                    source=file.filename,
                    text=body,
                    metadata={
                        "parser": self.name,
                        "section": "body",
                        "subject": headers.get("subject"),
                    },
                )
            )
        for attachment in attachments:
            result.chunks.append(
                ParsedDocument(
                    source=file.filename,
                    text="",
                    metadata={
                        "parser": self.name,
                        "section": "attachment",
                        **attachment,
                    },
                )
            )

        return result
