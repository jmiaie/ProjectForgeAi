from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from automations.temporal_activities import run_automation_activity, run_due_automations_activity


@workflow.defn(name="RunAutomationWorkflow")
class RunAutomationWorkflow:
    @workflow.run
    async def run(self, project_id: str, automation_id: str, attempt: int = 1) -> dict:
        return await workflow.execute_activity(
            run_automation_activity,
            args=[project_id, automation_id, attempt],
            start_to_close_timeout=timedelta(minutes=10),
        )


@workflow.defn(name="DueAutomationsWorkflow")
class DueAutomationsWorkflow:
    @workflow.run
    async def run(self) -> dict:
        return await workflow.execute_activity(
            run_due_automations_activity,
            start_to_close_timeout=timedelta(minutes=10),
        )
