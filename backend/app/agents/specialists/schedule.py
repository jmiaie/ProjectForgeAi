"""Schedule specialist: produces milestones / Gantt-ready tasks."""

from __future__ import annotations

from app.agents.specialists.base import SpecialistAgent
from app.agents.state import OrchestratorState, SpecialistOutput


class ScheduleAgent(SpecialistAgent):
    name = "schedule"

    def system_prompt(self, state: OrchestratorState) -> str:
        return (
            "You are the Schedule specialist for ProjectForge AI. "
            "Produce a numbered list of milestones and tasks suitable for a Gantt chart. "
            "Each line should be of the form 'Milestone: <name> (duration: <days>d)' or "
            "'Task: <name> (depends on: <prereq>)'. Be specific and avoid placeholder language."
        )

    def parse_response(
        self, text: str, state: OrchestratorState
    ) -> SpecialistOutput:
        lines = self.split_lines(text)
        milestones = [line for line in lines if line.lower().startswith("milestone")]
        tasks = [line for line in lines if line.lower().startswith("task")]
        artefacts = self.to_artefacts(milestones, "milestone") + self.to_artefacts(
            tasks, "task"
        )
        summary = (
            f"Drafted {len(milestones)} milestone(s) and {len(tasks)} task(s)."
            if (milestones or tasks)
            else "No schedule items extracted."
        )
        return SpecialistOutput(
            agent=self.name,
            summary=summary,
            artefacts=artefacts or self.to_artefacts(lines, "schedule_item"),
            warnings=[],
        )
