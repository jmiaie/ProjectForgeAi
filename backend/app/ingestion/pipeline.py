from fastapi import UploadFile

from app.storage.locus_adapter import LocusAdapter
from app.storage.ompa_adapter import OmpaAdapter


class IngestionPipeline:
    async def process_files(self, project_id: str, files: list[UploadFile]) -> dict:
        locus = LocusAdapter(project_id)
        ompa = OmpaAdapter(project_id)

        # Phase 1 parser hooks (PDF, image, email) are added incrementally.
        for file in files:
            await locus.index_files([f"{file.filename}:stub_chunk"])
            await ompa.record_decision(f"Processed {file.filename}")
        return {"status": "ingested", "files": len(files)}
