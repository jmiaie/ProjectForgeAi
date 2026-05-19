"""Local Locus engine: persistent, BM25-scored vectorless retrieval.

This is a production-shaped fallback for the upstream ``locus`` submodule.
It writes a project-scoped JSON index to disk and serves retrieval queries
via the Okapi BM25 scoring function — substantially better than the
substring scan used by the v14 scaffold.

Key features:

* Persistent JSON storage (atomic writes via ``os.replace``).
* Inverted index keyed by lowercased ASCII tokens.
* BM25 ranking with configurable ``k1`` / ``b`` parameters.
* Metadata filter support (``filters={"page": 3}``).
* Idempotent indexing: re-indexing the same content does not duplicate.
"""

from __future__ import annotations

import json
import math
import os
import re
import tempfile
import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Iterable


_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def _tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in _TOKEN_RE.finditer(text or "")]


def _content_hash(text: str, metadata: dict[str, Any]) -> str:
    import hashlib

    payload = json.dumps(
        {"text": text, "metadata": metadata}, sort_keys=True, default=str
    )
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]


@dataclass
class IndexedChunk:
    id: str
    text: str
    tokens: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "tokens": self.tokens,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IndexedChunk":
        return cls(
            id=data["id"],
            text=data["text"],
            tokens=list(data.get("tokens", [])),
            metadata=data.get("metadata", {}),
        )


class LocusEngine:
    """File-backed BM25 retrieval engine for a single project store."""

    def __init__(
        self,
        store_path: str,
        *,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        self.store_path = store_path
        self.k1 = k1
        self.b = b
        self._lock = threading.Lock()
        os.makedirs(self.store_path, exist_ok=True)
        self._index_path = os.path.join(self.store_path, "index.json")
        self._chunks: dict[str, IndexedChunk] = {}
        self._content_hashes: dict[str, str] = {}  # hash -> chunk_id
        self._inverted: dict[str, dict[str, int]] = {}  # token -> {chunk_id: tf}
        self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def index(self, chunks: Iterable[dict[str, Any]]) -> dict[str, int]:
        """Index a batch of chunk dicts. Returns ``{"added": n, "skipped": m}``.

        Each input chunk should have at least a ``text`` field; ``metadata``
        and ``source`` are stored verbatim. Duplicate content (same text +
        metadata) is skipped so re-runs are idempotent.
        """

        added = 0
        skipped = 0
        with self._lock:
            for chunk in chunks:
                text = (chunk.get("text") or "").strip()
                if not text:
                    skipped += 1
                    continue
                metadata = dict(chunk.get("metadata") or {})
                if "source" in chunk and "source" not in metadata:
                    metadata["source"] = chunk["source"]
                content_hash = _content_hash(text, metadata)
                if content_hash in self._content_hashes:
                    skipped += 1
                    continue
                chunk_id = chunk.get("id") or f"chunk_{uuid.uuid4().hex[:12]}"
                tokens = _tokenize(text)
                indexed = IndexedChunk(
                    id=chunk_id, text=text, tokens=tokens, metadata=metadata
                )
                self._chunks[chunk_id] = indexed
                self._content_hashes[content_hash] = chunk_id
                for token in tokens:
                    self._inverted.setdefault(token, {})
                    self._inverted[token][chunk_id] = (
                        self._inverted[token].get(chunk_id, 0) + 1
                    )
                added += 1
            self._save()
        return {"added": added, "skipped": skipped, "total": len(self._chunks)}

    def retrieve(
        self,
        query: str,
        limit: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Return the top-``limit`` chunks scored by BM25 against ``query``.

        ``filters`` is a flat ``{metadata_key: value}`` dict; only chunks
        whose metadata matches every entry are considered.
        """

        with self._lock:
            tokens = _tokenize(query)
            if not tokens or not self._chunks:
                return []

            n_docs = len(self._chunks)
            avg_dl = (
                sum(len(chunk.tokens) for chunk in self._chunks.values()) / n_docs
            )

            scores: dict[str, float] = {}
            for token in tokens:
                postings = self._inverted.get(token)
                if not postings:
                    continue
                df = len(postings)
                idf = math.log(1 + (n_docs - df + 0.5) / (df + 0.5))
                for chunk_id, tf in postings.items():
                    chunk = self._chunks[chunk_id]
                    dl = max(len(chunk.tokens), 1)
                    norm = 1 - self.b + self.b * (dl / avg_dl)
                    score = idf * ((tf * (self.k1 + 1)) / (tf + self.k1 * norm))
                    scores[chunk_id] = scores.get(chunk_id, 0.0) + score

            results: list[tuple[float, IndexedChunk]] = []
            for chunk_id, score in scores.items():
                chunk = self._chunks[chunk_id]
                if filters and not self._matches_filters(chunk, filters):
                    continue
                results.append((score, chunk))
            results.sort(key=lambda item: item[0], reverse=True)

            output: list[dict[str, Any]] = []
            for score, chunk in results[:limit]:
                output.append(
                    {
                        "id": chunk.id,
                        "text": chunk.text,
                        "score": round(score, 6),
                        "metadata": chunk.metadata,
                    }
                )
            return output

    def stats(self) -> dict[str, Any]:
        with self._lock:
            total_tokens = sum(len(c.tokens) for c in self._chunks.values())
            return {
                "total_chunks": len(self._chunks),
                "total_tokens": total_tokens,
                "unique_terms": len(self._inverted),
                "store_path": self.store_path,
            }

    def clear(self) -> None:
        with self._lock:
            self._chunks.clear()
            self._content_hashes.clear()
            self._inverted.clear()
            self._save()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    @staticmethod
    def _matches_filters(
        chunk: IndexedChunk, filters: dict[str, Any]
    ) -> bool:
        for key, expected in filters.items():
            if chunk.metadata.get(key) != expected:
                return False
        return True

    def _load(self) -> None:
        if not os.path.exists(self._index_path):
            return
        try:
            with open(self._index_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError):
            return
        for raw in data.get("chunks", []):
            chunk = IndexedChunk.from_dict(raw)
            self._chunks[chunk.id] = chunk
            self._content_hashes[
                _content_hash(chunk.text, chunk.metadata)
            ] = chunk.id
            for token in chunk.tokens:
                self._inverted.setdefault(token, {})
                self._inverted[token][chunk.id] = (
                    self._inverted[token].get(chunk.id, 0) + 1
                )

    def _save(self) -> None:
        payload = {"chunks": [chunk.to_dict() for chunk in self._chunks.values()]}
        directory = os.path.dirname(self._index_path) or "."
        fd, tmp_path = tempfile.mkstemp(prefix=".locus-", dir=directory)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh)
            os.replace(tmp_path, self._index_path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
