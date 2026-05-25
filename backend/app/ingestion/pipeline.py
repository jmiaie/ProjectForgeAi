import inspect
from io import BytesIO
from pathlib import Path
from typing import Any

from ingestion.manifest import IngestionManifestStore
from ingestion.parsers.base import ParsedChunk, ParsedDocument
from ingestion.parsers.common.cad_bim import parse_dwg, parse_ifc
from ingestion.parsers.common.codebase import parse_code_archive
from ingestion.parsers.common.email import parse_email
from ingestion.parsers.common.image import parse_image
from ingestion.parsers.common.mbox import parse_mbox
from ingestion.parsers.common.office import parse_office
from ingestion.parsers.common.pdf import parse_pdf
from storage.locus_adapter import LocusAdapter
from storage.ompa_adapter import OmpaAdapter


class IngestionPipeline:
    def __init__(self, manifest_store: IngestionManifestStore | None = None):
        self.manifest_store = manifest_store or IngestionManifestStore()

    async def process_files(self, project_id: str, files: list[Any]):
        locus = LocusAdapter(project_id)
        ompa = OmpaAdapter(project_id)
        session = await ompa.session_start()

        files_processed = 0
        chunks_indexed = 0
        warnings: list[str] = []
        parsed_documents: list[ParsedDocument] = []
        for file in files:
            parsed = await self._parse_file(file)
            parsed_documents.append(parsed)
            chunk_dicts = [chunk.as_dict() for chunk in parsed.chunks]
            if chunk_dicts:
                await locus.index_files(chunk_dicts)
            await ompa.record_decision(
                f"Processed {parsed.source}: {len(chunk_dicts)} chunks via {parsed.metadata['parser']}"
            )
            files_processed += 1
            chunks_indexed += len(chunk_dicts)
            warnings.extend(parsed.warnings)

        storage = {
            "locus": locus.status(),
            "ompa": ompa.status(),
            "native_ready": locus.native and ompa.native,
        }
        manifest = self.manifest_store.write(
            project_id=project_id,
            documents=parsed_documents,
            storage=storage,
            session=session,
        )
        return {
            "status": "ingested",
            "project_id": project_id,
            "files_processed": files_processed,
            "chunks_indexed": chunks_indexed,
            "warnings": warnings,
            "manifest": {
                "path": manifest["path"],
                "files_processed": manifest["files_processed"],
                "chunks_indexed": manifest["chunks_indexed"],
                "warnings": manifest["warnings"],
            },
            "session": session,
            "storage": storage,
        }

    async def append_documents(self, project_id: str, documents: list[ParsedDocument]) -> dict:
        locus = LocusAdapter(project_id)
        ompa = OmpaAdapter(project_id)
        session = await ompa.session_start()

        chunks_indexed = 0
        warnings: list[str] = []
        for parsed in documents:
            chunk_dicts = [chunk.as_dict() for chunk in parsed.chunks]
            if chunk_dicts:
                await locus.index_files(chunk_dicts)
            await ompa.record_decision(
                f"Appended {parsed.source}: {len(chunk_dicts)} chunks via {parsed.metadata.get('parser')}"
            )
            chunks_indexed += len(chunk_dicts)
            warnings.extend(parsed.warnings)

        storage = {
            "locus": locus.status(),
            "ompa": ompa.status(),
            "native_ready": locus.native and ompa.native,
        }
        manifest = self.manifest_store.append(
            project_id=project_id,
            documents=documents,
            storage=storage,
            session=session,
        )
        return {
            "status": "appended",
            "project_id": project_id,
            "files_processed": len(documents),
            "chunks_indexed": chunks_indexed,
            "warnings": warnings,
            "manifest": {
                "path": manifest["path"],
                "files_processed": manifest["files_processed"],
                "chunks_indexed": manifest["chunks_indexed"],
                "warnings": manifest["warnings"],
            },
            "session": session,
            "storage": storage,
        }

    async def _parse_file(self, file: Any) -> ParsedDocument:
        filename = getattr(file, "filename", None) or getattr(file, "name", None) or str(file)
        suffix = Path(filename).suffix.lower()

        if suffix == ".pdf":
            payload = await self._read_upload_payload(file)
            if payload is not None:
                return parse_pdf(BytesIO(payload), filename=filename)

            path = Path(str(file))
            if path.exists():
                return parse_pdf(path, filename=filename)

            return ParsedDocument(
                source=filename,
                chunks=[],
                metadata={"parser": "pdf", "source": filename, "chunk_count": 0},
                warnings=[f"{filename}: PDF reference is not available on the backend filesystem"],
            )

        if suffix in {".eml"}:
            return await self._parse_payload_or_path(file, filename, parse_email)

        if suffix in {".mbox"}:
            return await self._parse_payload_or_path(file, filename, parse_mbox)

        if suffix in {".docx", ".xlsx", ".pptx"}:
            return await self._parse_payload_or_path(file, filename, parse_office)

        if suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".tif", ".tiff", ".bmp"}:
            return await self._parse_payload_or_path(file, filename, parse_image)

        lower_name = filename.lower()
        if lower_name.endswith(".ifc"):
            return await self._parse_payload_or_path(file, filename, parse_ifc)
        if lower_name.endswith(".dwg"):
            return await self._parse_payload_or_path(file, filename, parse_dwg)
        if lower_name.endswith((".zip", ".tar", ".tar.gz", ".tgz")):
            return await self._parse_payload_or_path(file, filename, parse_code_archive)

        chunk = ParsedChunk(
            source=filename,
            text="",
            metadata={
                "parser": "external_reference",
                "source": filename,
                "chunk_count": 1,
            },
        )
        return ParsedDocument(
            source=filename,
            chunks=[chunk],
            metadata={"parser": "external_reference", "source": filename, "chunk_count": 1},
            warnings=[f"{filename}: no parser registered for {suffix or 'unknown file type'}"],
        )

    async def _parse_payload_or_path(self, file: Any, filename: str, parser):
        payload = await self._read_upload_payload(file)
        if payload is not None:
            return parser(BytesIO(payload), filename=filename)

        path = Path(str(file))
        if path.exists():
            return parser(path, filename=filename)

        return ParsedDocument(
            source=filename,
            chunks=[],
            metadata={
                "parser": Path(filename).suffix.lower().removeprefix(".") or "unknown",
                "source": filename,
                "chunk_count": 0,
            },
            warnings=[f"{filename}: file reference is not available on the backend filesystem"],
        )

    async def _read_upload_payload(self, file: Any) -> bytes | None:
        file_obj = getattr(file, "file", None)
        if file_obj is not None and hasattr(file_obj, "read"):
            position = file_obj.tell() if hasattr(file_obj, "tell") else None
            if hasattr(file_obj, "seek"):
                file_obj.seek(0)
            data = file_obj.read()
            if position is not None and hasattr(file_obj, "seek"):
                file_obj.seek(position)
            return data

        read = getattr(file, "read", None)
        if read is None or isinstance(file, (str, Path)):
            return None

        result = read()
        if inspect.isawaitable(result):
            result = await result
        if isinstance(result, str):
            return result.encode()
        return result
