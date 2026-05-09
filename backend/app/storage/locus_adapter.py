import os


class LocusAdapter:
    def __init__(self, project_id: str):
        self.store_path = f"./.locus/project_{project_id}"
        os.makedirs(self.store_path, exist_ok=True)
        self._fallback_chunks: list[str] = []

        try:
            from locus import LocusEngine  # type: ignore
        except ImportError:
            self.engine = None
        else:
            self.engine = LocusEngine(store_path=self.store_path)

    async def index_files(self, chunks: list[str]) -> None:
        if self.engine is None:
            self._fallback_chunks.extend(chunks)
            return
        self.engine.index(chunks)

    async def retrieve(self, query: str, limit: int = 10) -> list[str]:
        if self.engine is None:
            return [chunk for chunk in self._fallback_chunks if query.lower() in chunk.lower()][:limit]
        return self.engine.retrieve(query, limit=limit)
