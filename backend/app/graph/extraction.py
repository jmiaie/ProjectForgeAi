import json
import re
from dataclasses import dataclass
from typing import Any

from core.llm_router import LLMRequest, LLMRouter


@dataclass(frozen=True)
class ExtractedFact:
    label: str
    name: str
    source: str
    source_hash: str | None
    chunk_index: int | None
    excerpt: str
    extractor: str
    sequence: int | None = None
    severity: str | None = None


EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def extract_facts_heuristic(chunk: dict[str, Any]) -> list[ExtractedFact]:
    text = str(chunk.get("text", ""))
    metadata = chunk.get("metadata") or {}
    source = str(chunk.get("source") or metadata.get("source") or "unknown")
    source_hash = metadata.get("source_hash")
    chunk_index = metadata.get("chunk_index")
    facts: list[ExtractedFact] = []
    seen: set[tuple[str, str]] = set()

    for line in text.splitlines():
        normalized = line.strip()
        if not normalized:
            continue
        lower = normalized.lower()

        if lower.startswith("from:") or lower.startswith("to:"):
            email = EMAIL_PATTERN.search(normalized)
            name = email.group(0) if email else normalized.split(":", 1)[-1].strip()
            _add_fact(facts, seen, "Stakeholder", name, source, source_hash, chunk_index, normalized, "heuristic")
            continue

        if any(token in lower for token in ("risk", "blocker", "issue")):
            _add_fact(
                facts,
                seen,
                "Risk",
                normalized[:120],
                source,
                source_hash,
                chunk_index,
                normalized,
                "heuristic",
                severity="medium",
            )
            continue

        if any(token in lower for token in ("milestone", "kickoff", "deadline", "go-live")):
            _add_fact(
                facts,
                seen,
                "Milestone",
                normalized[:120],
                source,
                source_hash,
                chunk_index,
                normalized,
                "heuristic",
                sequence=len([fact for fact in facts if fact.label == "Milestone"]) + 1,
            )
            continue

        if any(token in lower for token in ("task", "action", "deliverable", "todo")):
            _add_fact(
                facts,
                seen,
                "Task",
                normalized[:120],
                source,
                source_hash,
                chunk_index,
                normalized,
                "heuristic",
                sequence=len([fact for fact in facts if fact.label == "Task"]) + 1,
            )

    return facts


async def extract_facts(
    chunk: dict[str, Any],
    *,
    project_id: str,
    use_llm: bool,
    llm_router: LLMRouter | None = None,
) -> list[ExtractedFact]:
    if not use_llm:
        return extract_facts_heuristic(chunk)

    router = llm_router or LLMRouter()
    metadata = chunk.get("metadata") or {}
    source = str(chunk.get("source") or metadata.get("source") or "unknown")
    prompt = (
        "Extract project facts as JSON with keys stakeholders, tasks, risks, milestones. "
        "Each item must include name and excerpt fields. "
        f"Source document: {source}. Text:\n{chunk.get('text', '')[:4000]}"
    )
    try:
        response = await router.call(
            LLMRequest(
                project_id=project_id,
                task_type="reasoning",
                messages=[{"role": "user", "content": prompt}],
            )
        )
        payload = json.loads(response)
        return _facts_from_llm_payload(payload, chunk, source)
    except Exception:
        return extract_facts_heuristic(chunk)


def _facts_from_llm_payload(payload: dict[str, Any], chunk: dict[str, Any], source: str) -> list[ExtractedFact]:
    metadata = chunk.get("metadata") or {}
    source_hash = metadata.get("source_hash")
    chunk_index = metadata.get("chunk_index")
    facts: list[ExtractedFact] = []
    seen: set[tuple[str, str]] = set()

    mapping = {
        "stakeholders": "Stakeholder",
        "tasks": "Task",
        "risks": "Risk",
        "milestones": "Milestone",
    }
    for key, label in mapping.items():
        for index, item in enumerate(payload.get(key, []), start=1):
            if isinstance(item, str):
                name = item
                excerpt = item
            else:
                name = str(item.get("name") or item.get("title") or f"{label} {index}")
                excerpt = str(item.get("excerpt") or name)
            _add_fact(
                facts,
                seen,
                label,
                name,
                source,
                source_hash,
                chunk_index,
                excerpt,
                "llm",
                sequence=index if label in {"Task", "Milestone"} else None,
                severity=str(item.get("severity")) if isinstance(item, dict) and item.get("severity") else None,
            )
    return facts


def _add_fact(
    facts: list[ExtractedFact],
    seen: set[tuple[str, str]],
    label: str,
    name: str,
    source: str,
    source_hash: str | None,
    chunk_index: int | None,
    excerpt: str,
    extractor: str,
    sequence: int | None = None,
    severity: str | None = None,
) -> None:
    key = (label, name.lower())
    if key in seen:
        return
    seen.add(key)
    facts.append(
        ExtractedFact(
            label=label,
            name=name,
            source=source,
            source_hash=source_hash,
            chunk_index=chunk_index,
            excerpt=excerpt,
            extractor=extractor,
            sequence=sequence,
            severity=severity,
        )
    )
