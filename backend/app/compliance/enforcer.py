from dataclasses import dataclass


@dataclass
class ComplianceProfile:
    category: str = "standard"


def get_compliance_profile(project_id: str) -> ComplianceProfile:
    # Placeholder until per-project compliance persistence is wired.
    return ComplianceProfile(category="standard")
