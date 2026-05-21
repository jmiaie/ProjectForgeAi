"""Compliance specialist: maps controls to the project's compliance tier."""

from __future__ import annotations

from app.agents.specialists.base import SpecialistAgent
from app.agents.state import OrchestratorState, SpecialistOutput


CATEGORY_CONTROLS: dict[str, list[str]] = {
    "standard": [
        "Data classification & handling baseline",
        "Access control review (least privilege)",
        "Backup & retention policy",
    ],
    "hipaa": [
        "PHI access logging (45 CFR 164.312(b))",
        "Encryption at rest & in transit (164.312(a)(2)(iv) / (e)(2)(ii))",
        "Business Associate Agreements with all subprocessors",
        "Breach notification workflow (164.404)",
    ],
    "soc2": [
        "Change management approvals (CC8.1)",
        "Logical access reviews (CC6.2)",
        "Vendor risk assessment (CC9.2)",
        "Incident response runbook (CC7.3)",
    ],
    "gdpr": [
        "Lawful basis register & DPIA per processing activity",
        "Data subject access request workflow",
        "Cross-border transfer mechanism (SCCs / adequacy)",
        "Records of Processing Activities (Art. 30)",
    ],
    "legal": [
        "Litigation hold procedure",
        "Privileged communications routing",
        "Chain of custody tracking",
    ],
}


class ComplianceAgent(SpecialistAgent):
    name = "compliance"

    def system_prompt(self, state: OrchestratorState) -> str:
        category = state.get("compliance_category", "standard")
        controls = CATEGORY_CONTROLS.get(category, CATEGORY_CONTROLS["standard"])
        bullet_list = "\n".join(f"- {control}" for control in controls)
        return (
            f"You are the Compliance specialist for ProjectForge AI. The project compliance "
            f"category is '{category}'. The following baseline controls apply:\n{bullet_list}\n"
            "For each control, output a single line of the form: "
            "'Control: <name> | Owner: <role> | Evidence: <evidence_artifact>'."
        )

    def parse_response(
        self, text: str, state: OrchestratorState
    ) -> SpecialistOutput:
        category = state.get("compliance_category", "standard")
        baseline = CATEGORY_CONTROLS.get(category, CATEGORY_CONTROLS["standard"])
        lines = [line for line in self.split_lines(text) if "Control:" in line]
        artefacts = [
            {"kind": "compliance_control", "category": category, "value": line}
            for line in lines
        ]
        if not artefacts:
            artefacts = [
                {
                    "kind": "compliance_control",
                    "category": category,
                    "value": f"Control: {control} | Owner: TBD | Evidence: TBD",
                }
                for control in baseline
            ]
        return SpecialistOutput(
            agent=self.name,
            summary=f"Mapped {len(artefacts)} {category} control(s).",
            artefacts=artefacts,
            warnings=[],
        )
