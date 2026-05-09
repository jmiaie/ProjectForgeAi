"""Contracts specialist: drafts SOW / MSA / NDA template scaffolding."""

from __future__ import annotations

from app.agents.specialists.base import SpecialistAgent
from app.agents.state import OrchestratorState, SpecialistOutput


CONTRACT_TYPES = ("SOW", "MSA", "NDA")


class ContractsAgent(SpecialistAgent):
    name = "contracts"

    def system_prompt(self, state: OrchestratorState) -> str:
        category = state.get("compliance_category", "standard")
        return (
            "You are the Contracts specialist for ProjectForge AI. "
            f"Compliance category is '{category}'. "
            "Produce three short templates, each prefixed with its label on its own line: "
            f"{', '.join(CONTRACT_TYPES)}. "
            "After each label, output the template body. Separate the three templates with a "
            "line containing only '==='. Insert clearly named placeholders in [SQUARE_BRACKETS]."
        )

    def parse_response(
        self, text: str, state: OrchestratorState
    ) -> SpecialistOutput:
        sections = [section.strip() for section in text.split("===") if section.strip()]
        artefacts = []
        for section in sections:
            label = "unknown"
            for kind in CONTRACT_TYPES:
                if section.upper().startswith(kind):
                    label = kind.lower()
                    section = section[len(kind):].lstrip(": \n")
                    break
            artefacts.append(
                {"kind": "contract_template", "label": label, "value": section}
            )
        if not artefacts:
            artefacts.append(
                {"kind": "contract_template", "label": "raw", "value": text.strip()}
            )
        return SpecialistOutput(
            agent=self.name,
            summary=f"Drafted {len(artefacts)} contract template(s).",
            artefacts=artefacts,
            warnings=[],
        )
