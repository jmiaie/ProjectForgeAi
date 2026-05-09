from dataclasses import dataclass

from core.config import settings


@dataclass(frozen=True)
class ComplianceProfile:
    project_id: str
    category: str
    allow_self_learning: bool = True


def get_compliance_profile(project_id: str) -> ComplianceProfile:
    category = settings.DEFAULT_COMPLIANCE.lower()
    restricted = category in {"hipaa", "legal"}
    return ComplianceProfile(
        project_id=project_id,
        category=category,
        allow_self_learning=not restricted,
    )
