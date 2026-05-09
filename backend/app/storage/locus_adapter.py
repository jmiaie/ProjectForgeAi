import os
from typing import Any

from core.config import settings
from storage.native_loader import (
    NativeIntegrationError,
    call_first_available,
    instantiate_with_path,
    load_symbol,
    maybe_await,
)


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
        self.project_id = project_id
        self.store_path = os.path.join(settings.LOCUS_STORE_ROOT, f"project_{project_id}")
        os.makedirs(self.store_path, exist_ok=True)
        self.native = True
        self.warning: str | None = None
        try:
            LocusEngine = load_symbol(settings.LOCUS_ENGINE, settings.LOCUS_SOURCE_PATH)
            self.engine = instantiate_with_path(LocusEngine, "store_path", self.store_path)
        except NativeIntegrationError as exc:
            if settings.REQUIRE_NATIVE_LOCUS_OMPA:
                raise
            self.native = False
            self.warning = str(exc)
            self.engine = InMemoryLocusEngine(store_path=self.store_path)

    async def index_files(self, chunks: list[Any]) -> None:
        await call_first_available(
            self.engine,
            ("index", "index_files", "add_documents", "add_chunks"),
            chunks,
        )

    async def retrieve(self, query: str, limit: int = 10):
        try:
            return await call_first_available(
                self.engine,
                ("retrieve", "search", "query"),
                query,
                limit=limit,
            )
        except TypeError:
            result = self.engine.retrieve(query)
            result = await maybe_await(result)
            return result[:limit] if isinstance(result, list) else result

    def status(self) -> dict[str, Any]:
        return {
            "name": "locus",
            "native": self.native,
            "engine": self.engine.__class__.__name__,
            "store_path": self.store_path,
            "warning": self.warning,
        }
