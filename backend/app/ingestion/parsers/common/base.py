"""Shared parser primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ParsedDocument:
    """A single chunk of parsed content ready for indexing."""

    source: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParserResult:
    """Aggregate output from a parser run."""

    chunks: list[ParsedDocument] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class FileLike(Protocol):
    """Subset of ``starlette.UploadFile`` actually used by parsers."""

    filename: str

    async def read(self) -> bytes: ...  # noqa: D401 - protocol method


class Parser(Protocol):
    """Common parser interface."""

    async def parse(self, file: FileLike) -> ParserResult: ...
