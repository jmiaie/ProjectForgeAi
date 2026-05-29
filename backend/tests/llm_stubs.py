"""Deterministic LLM responses for pytest (no live provider calls)."""

from __future__ import annotations

from app.core.llm_router import LLMRequest


async def stub_llm_call(self, req: LLMRequest) -> str:
    """Replace :meth:`~app.core.llm_router.LLMRouter.call` during tests."""

    messages = req.messages or []
    system = next(
        (str(m.get("content", "")) for m in messages if m.get("role") == "system"),
        "",
    )
    user = next(
        (str(m.get("content", "")) for m in messages if m.get("role") == "user"),
        "",
    )
    combined = f"{system}\n{user}".lower()

    if "orchestrator" in combined and "specialist agents to invoke" in combined:
        return "schedule\ncomms\ncontracts\ncompliance\nrisk"

    if "schedule specialist" in combined:
        return (
            "Milestone: Kickoff complete (duration: 5d)\n"
            "Milestone: Design review (duration: 10d)\n"
            "Task: Draft scope (depends on: kickoff)\n"
        )

    if "communications specialist" in combined:
        return (
            "Kickoff email to stakeholders.\n"
            "---\n"
            "Weekly status update template.\n"
            "---\n"
            "Escalation message template.\n"
        )

    if "contracts specialist" in combined:
        return (
            "SOW\nScope of work for [CLIENT].\n"
            "===\n"
            "MSA\nMaster services agreement for [PARTIES].\n"
            "===\n"
            "NDA\nMutual NDA with [TERM].\n"
        )

    if "compliance specialist" in combined:
        return (
            "Control: Access logging | Owner: Security | Evidence: audit_log\n"
            "Control: Encryption at rest | Owner: Platform | Evidence: kms_config\n"
        )

    if "risk specialist" in combined:
        return (
            "Risk: Vendor delay | Likelihood: medium | Impact: high | "
            "Mitigation: penalty clause in contract"
        )

    return "[test-stub] acknowledged"
