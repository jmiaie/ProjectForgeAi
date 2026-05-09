from typing import Any

from storage.locus_adapter import LocusAdapter
from storage.ompa_adapter import OmpaAdapter


class IngestionPipeline:
    async def process_files(self, project_id: str, files: list[Any]):
        locus = LocusAdapter(project_id)
        ompa = OmpaAdapter(project_id)

        indexed = 0
        for file in files:
            filename = getattr(file, "filename", str(file))
            chunk = {
                "source": filename,
                "text": "",
                "metadata": {"parser": "placeholder"},
            }
            await locus.index_files([chunk])
            await ompa.record_decision(f"Processed {filename}")
            indexed += 1

        return {"status": "ingested", "project_id": project_id, "files_processed": indexed}
