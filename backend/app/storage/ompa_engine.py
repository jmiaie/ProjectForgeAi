"""Local OMPA engine: persistent decision / observation journal.

Production-shaped fallback for the upstream ``ompa`` submodule. Each
project gets a vault directory containing:

* ``entries.jsonl`` — append-only structured journal (one JSON object per line).
* ``sessions.json``  — open + recently-closed sessions with metadata.

The engine classifies free-form messages into a small set of buckets
(decision / observation / action / error / milestone / note) using cheap
regex hints. Callers may pass an explicit ``classification`` to bypass.
"""

from __future__ import annotations

import json
import os
import re
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable


CLASSIFICATIONS = (
    "decision",
    "observation",
    "action",
    "error",
    "milestone",
    "note",
)

_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("error", re.compile(r"\b(error|fail(ed)?|exception|traceback|broke)\b", re.I)),
    ("decision", re.compile(r"\b(decide(d)?|chose|approved|rejected|ruled)\b", re.I)),
    ("milestone", re.compile(r"\b(milestone|completed|launched|shipped|kickoff)\b", re.I)),
    ("action", re.compile(r"\b(will|next|todo|action item|follow[- ]?up)\b", re.I)),
    ("observation", re.compile(r"\b(noticed|observed|saw|appears|seems)\b", re.I)),
]


def _classify(message: str) -> str:
    for kind, pattern in _RULES:
        if pattern.search(message):
            return kind
    return "note"


@dataclass
class JournalEntry:
    id: str
    session_id: str | None
    classification: str
    message: str
    tags: list[str] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "classification": self.classification,
            "message": self.message,
            "tags": self.tags,
            "properties": self.properties,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JournalEntry":
        return cls(
            id=data["id"],
            session_id=data.get("session_id"),
            classification=data.get("classification", "note"),
            message=data.get("message", ""),
            tags=list(data.get("tags", [])),
            properties=data.get("properties", {}),
            timestamp=data.get("timestamp")
            or datetime.now(timezone.utc).isoformat(),
        )


class OmpaEngine:
    """Append-only journal + lightweight session tracker."""

    def __init__(self, vault_path: str) -> None:
        self.vault_path = vault_path
        os.makedirs(self.vault_path, exist_ok=True)
        self._entries_path = os.path.join(self.vault_path, "entries.jsonl")
        self._sessions_path = os.path.join(self.vault_path, "sessions.json")
        self._lock = threading.Lock()
        self._sessions: dict[str, dict[str, Any]] = {}
        self._current_session_id: str | None = None
        self._load_sessions()

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------
    def session_start(self, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        with self._lock:
            session_id = f"sess_{uuid.uuid4().hex[:16]}"
            session = {
                "session_id": session_id,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "ended_at": None,
                "metadata": dict(metadata or {}),
                "entry_count": 0,
            }
            self._sessions[session_id] = session
            self._current_session_id = session_id
            self._save_sessions()
            return dict(session)

    def session_end(self, session_id: str | None = None) -> dict[str, Any] | None:
        with self._lock:
            target = session_id or self._current_session_id
            if target is None or target not in self._sessions:
                return None
            self._sessions[target]["ended_at"] = datetime.now(
                timezone.utc
            ).isoformat()
            if self._current_session_id == target:
                self._current_session_id = None
            self._save_sessions()
            return dict(self._sessions[target])

    def current_session_id(self) -> str | None:
        return self._current_session_id

    def sessions(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(session) for session in self._sessions.values()]

    # ------------------------------------------------------------------
    # Journal
    # ------------------------------------------------------------------
    def classify(
        self,
        message: str,
        *,
        classification: str | None = None,
        tags: list[str] | None = None,
        properties: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Append a structured entry to the journal and return it."""

        with self._lock:
            target_session = session_id or self._current_session_id
            kind = classification or _classify(message)
            if kind not in CLASSIFICATIONS:
                kind = "note"
            entry = JournalEntry(
                id=f"entry_{uuid.uuid4().hex[:16]}",
                session_id=target_session,
                classification=kind,
                message=message,
                tags=list(tags or []),
                properties=dict(properties or {}),
            )
            with open(self._entries_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry.to_dict()) + "\n")
            if target_session and target_session in self._sessions:
                self._sessions[target_session]["entry_count"] += 1
                self._save_sessions()
            return entry.to_dict()

    def entries(
        self,
        *,
        session_id: str | None = None,
        classification: str | None = None,
        tags: Iterable[str] | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        with self._lock:
            results: list[dict[str, Any]] = []
            if not os.path.exists(self._entries_path):
                return results
            with open(self._entries_path, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if session_id and data.get("session_id") != session_id:
                        continue
                    if classification and data.get("classification") != classification:
                        continue
                    if tags:
                        entry_tags = set(data.get("tags", []))
                        if not entry_tags.issuperset(set(tags)):
                            continue
                    results.append(data)
            results.sort(key=lambda d: d.get("timestamp", ""), reverse=True)
            if limit is not None:
                results = results[:limit]
            return results

    def stats(self) -> dict[str, Any]:
        with self._lock:
            counts: dict[str, int] = {kind: 0 for kind in CLASSIFICATIONS}
            total = 0
            if os.path.exists(self._entries_path):
                with open(self._entries_path, "r", encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        kind = data.get("classification", "note")
                        counts[kind] = counts.get(kind, 0) + 1
                        total += 1
            open_sessions = [
                s for s in self._sessions.values() if not s.get("ended_at")
            ]
            return {
                "total_entries": total,
                "by_classification": counts,
                "total_sessions": len(self._sessions),
                "open_sessions": len(open_sessions),
                "vault_path": self.vault_path,
            }

    # ------------------------------------------------------------------
    def _load_sessions(self) -> None:
        if not os.path.exists(self._sessions_path):
            return
        try:
            with open(self._sessions_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError):
            return
        self._sessions = {s["session_id"]: s for s in data.get("sessions", [])}
        self._current_session_id = data.get("current_session_id")

    def _save_sessions(self) -> None:
        payload = {
            "sessions": list(self._sessions.values()),
            "current_session_id": self._current_session_id,
        }
        directory = os.path.dirname(self._sessions_path) or "."
        import tempfile

        fd, tmp_path = tempfile.mkstemp(prefix=".ompa-", dir=directory)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh)
            os.replace(tmp_path, self._sessions_path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
