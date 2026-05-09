"""Catalogue of supported automation kinds.

Each :class:`AutomationKind` ties together a human-readable name, the default
recurrence (interval in seconds), and the specialist agent invoked when the
automation fires.
"""

from __future__ import annotations

from dataclasses import dataclass


_DAY = 86_400
_WEEK = 7 * _DAY


@dataclass(frozen=True)
class AutomationKind:
    name: str
    description: str
    default_interval_seconds: int
    specialist: str
    audit_action: str


AUTOMATION_KINDS: dict[str, AutomationKind] = {
    "status_report": AutomationKind(
        name="status_report",
        description="Recurring weekly status report drafted by the Comms specialist.",
        default_interval_seconds=_WEEK,
        specialist="comms",
        audit_action="automation.status_report.run",
    ),
    "kickoff": AutomationKind(
        name="kickoff",
        description="One-shot delayed kickoff communication.",
        default_interval_seconds=_DAY,
        specialist="comms",
        audit_action="automation.kickoff.run",
    ),
    "risk_reassessment": AutomationKind(
        name="risk_reassessment",
        description="Periodic risk register refresh by the Risk specialist.",
        default_interval_seconds=14 * _DAY,
        specialist="risk",
        audit_action="automation.risk_reassessment.run",
    ),
    "compliance_review": AutomationKind(
        name="compliance_review",
        description="Periodic compliance control review.",
        default_interval_seconds=30 * _DAY,
        specialist="compliance",
        audit_action="automation.compliance_review.run",
    ),
    "schedule_refresh": AutomationKind(
        name="schedule_refresh",
        description="Re-derive milestones / tasks from current context.",
        default_interval_seconds=_WEEK,
        specialist="schedule",
        audit_action="automation.schedule_refresh.run",
    ),
}


def get_automation_kind(name: str) -> AutomationKind:
    kind = AUTOMATION_KINDS.get(name)
    if kind is None:
        raise ValueError(
            f"Unknown automation kind '{name}'. "
            f"Available: {', '.join(AUTOMATION_KINDS)}"
        )
    return kind
