import os
from typing import Any


class InMemoryLocusEngine:
    def __init__(self, store_path: str):
        self.store_path = store_path
        self._chunks: list[Any] = []

    def index(self, chunks: list[Any]) -> None:
        self._chunks.extend(chunks)

    def retrieve(self, query: str, limit: int = 10) -> list[Any]:
        return self._chunks[:limit]


class LocusAdapter:
    def __init__(self, project_id: str):
        self.store_path = f"./.locus/project_{project_id}"
        os.makedirs(self.store_path, exist_ok=True)
        try:
            from locus import LocusEngine
        except ImportError:
            LocusEngine = InMemoryLocusEngine
        self.engine = LocusEngine(store_path=self.store_path)

    async def index_files(self, chunks: list[Any]) -> None:
        self.engine.index(chunks)

    async def retrieve(self, query: str, limit: int = 10):
        return self.engine.retrieve(query, limit=limit)
