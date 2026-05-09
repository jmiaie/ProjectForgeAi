from fastapi import UploadFile

from app.ingestion.parsers.common.email import parse_email
from app.ingestion.parsers.common.image import parse_image
from app.ingestion.parsers.common.pdf import parse_pdf
from app.storage.locus_adapter import LocusAdapter
from app.storage.ompa_adapter import OmpaAdapter


class IngestionPipeline:
    @staticmethod
    async def _parse_generic(file: UploadFile) -> list[str]:
        content = await file.read()
        if not content:
            return [f"file:{file.filename}:empty"]
        text = content.decode(errors="ignore")
        if text.strip():
            return [text[:4000]]
        return [f"file:{file.filename}:binary:{len(content)} bytes"]

    @staticmethod
    def _parser_name(file: UploadFile) -> str:
        filename = (file.filename or "").lower()
        content_type = (file.content_type or "").lower()

        if content_type == "application/pdf" or filename.endswith(".pdf"):
            return "pdf"
        if content_type.startswith("image/") or filename.endswith(
            (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff")
        ):
            return "image"
        if content_type.startswith("message/") or filename.endswith((".eml", ".msg")):
            return "email"
        return "generic"

    async def process_files(self, project_id: str, files: list[UploadFile]) -> dict:
        locus = LocusAdapter(project_id)
        ompa = OmpaAdapter(project_id)
        details: list[dict] = []
        total_chunks = 0

        for file in files:
            parser = self._parser_name(file)
            if parser == "pdf":
                chunks = await parse_pdf(file)
            elif parser == "image":
                chunks = await parse_image(file)
            elif parser == "email":
                chunks = await parse_email(file)
            else:
                chunks = await self._parse_generic(file)

            await locus.index_files(chunks)
            await ompa.record_decision(
                f"Processed file={file.filename} parser={parser} chunks={len(chunks)}"
            )

            details.append({"filename": file.filename, "parser": parser, "chunks": len(chunks)})
            total_chunks += len(chunks)

        return {
            "status": "ingested",
            "files": len(files),
            "chunks_indexed": total_chunks,
            "details": details,
        }
