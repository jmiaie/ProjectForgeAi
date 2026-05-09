import re
from dataclasses import dataclass, field


REDACTION_PATTERNS = {
    "email": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    "phone": re.compile(r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "mrn": re.compile(r"\b(?:MRN|Medical Record Number)[:#\s-]*[A-Z0-9-]{4,}\b", re.IGNORECASE),
    "dob": re.compile(r"\b(?:DOB|Date of Birth)[:#\s-]*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", re.IGNORECASE),
}


@dataclass(frozen=True)
class Redaction:
    type: str
    start: int
    end: int
    replacement: str


@dataclass(frozen=True)
class RedactionResult:
    text: str
    redactions: list[Redaction] = field(default_factory=list)

    def as_dicts(self) -> list[dict]:
        return [
            {
                "type": redaction.type,
                "start": redaction.start,
                "end": redaction.end,
                "replacement": redaction.replacement,
            }
            for redaction in self.redactions
        ]


def redact_text(text: str) -> RedactionResult:
    redactions: list[Redaction] = []
    output = text
    offset = 0
    matches = []
    for redaction_type, pattern in REDACTION_PATTERNS.items():
        for match in pattern.finditer(text):
            matches.append((match.start(), match.end(), redaction_type))

    for start, end, redaction_type in sorted(matches, key=lambda item: item[0]):
        adjusted_start = start + offset
        adjusted_end = end + offset
        replacement = f"[REDACTED_{redaction_type.upper()}]"
        output = output[:adjusted_start] + replacement + output[adjusted_end:]
        offset += len(replacement) - (end - start)
        redactions.append(
            Redaction(
                type=redaction_type,
                start=start,
                end=end,
                replacement=replacement,
            )
        )
    return RedactionResult(text=output, redactions=redactions)
