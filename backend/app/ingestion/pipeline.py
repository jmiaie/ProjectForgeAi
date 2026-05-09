import inspect
from io import BytesIO
from pathlib import Path
from typing import Any

from ingestion.parsers.common.pdf import ParsedDocument, parse_pdf
from storage.locus_adapter import LocusAdapter
from storage.ompa_adapter import OmpaAdapter


class IngestionPipeline:
    async def process_files(self, project_id: str, files: list[Any]):
        locus = LocusAdapter(project_id)
        ompa = OmpaAdapter(project_id)
        session = await ompa.session_start()

        files_processed = 0
        chunks_indexed = 0
        warnings: list[str] = []
        for file in files:
            parsed = await self._parse_file(file)
            chunk_dicts = [chunk.as_dict() for chunk in parsed.chunks]
            if chunk_dicts:
                await locus.index_files(chunk_dicts)
            await ompa.record_decision(
                f"Processed {parsed.source}: {len(chunk_dicts)} chunks via {parsed.metadata['parser']}"
            )
            files_processed += 1
            chunks_indexed += len(chunk_dicts)
            warnings.extend(parsed.warnings)

        return {
            "status": "ingested",
            "project_id": project_id,
            "files_processed": files_processed,
            "chunks_indexed": chunks_indexed,
            "warnings": warnings,
            "session": session,
            "storage": {
                "locus": locus.status(),
                "ompa": ompa.status(),
                "native_ready": locus.native and ompa.native,
            },
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

        chunk = {
            "source": filename,
            "text": "",
            "metadata": {
                "parser": "external_reference",
                "source": filename,
                "chunk_count": 1,
            },
        }
        return ParsedDocument(
            source=filename,
            chunks=[_DictBackedChunk(chunk)],
            metadata={"parser": "external_reference", "source": filename, "chunk_count": 1},
            warnings=[f"{filename}: no parser registered for {suffix or 'unknown file type'}"],
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


class _DictBackedChunk:
    def __init__(self, value: dict):
        self.value = value

    def as_dict(self) -> dict:
        return self.value
