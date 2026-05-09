from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4


class WorkflowScheduler:
    """Temporal-style workflow job registry with in-memory execution."""

    def __init__(self, state_backend: Any | None = None) -> None:
        self._state_backend = state_backend
        self._jobs_by_project: dict[str, dict[str, dict[str, Any]]] = {}
        self._runs_by_project: dict[str, list[dict[str, Any]]] = {}
        self._reports_by_project: dict[str, list[dict[str, Any]]] = {}

    @property
    def state_backend_mode(self) -> str:
        if self._state_backend is None:
            return "in_memory"
        return getattr(self._state_backend, "backend_mode", "in_memory")

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)

    @staticmethod
    def _now_iso() -> str:
        return WorkflowScheduler._now().isoformat()

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        normalized = normalized.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)

    @staticmethod
    def _schedule_delta(schedule_type: str, interval_minutes: int | None) -> timedelta:
        if interval_minutes is not None:
            if interval_minutes <= 0:
                raise ValueError("interval_minutes must be positive")
            return timedelta(minutes=interval_minutes)
        if schedule_type == "hourly":
            return timedelta(hours=1)
        if schedule_type == "daily":
            return timedelta(days=1)
        if schedule_type == "weekly":
            return timedelta(weeks=1)
        raise ValueError(f"Unsupported recurring schedule_type: {schedule_type}")

    def _next_run_after(
        self,
        schedule_type: str,
        interval_minutes: int | None,
        reference: datetime,
    ) -> datetime | None:
        if schedule_type == "once":
            return None
        return reference + self._schedule_delta(schedule_type, interval_minutes)

    def create_job(
        self,
        *,
        project_id: str,
        name: str,
        job_type: str,
        schedule_type: str,
        run_at: str | None = None,
        interval_minutes: int | None = None,
        payload: dict[str, Any] | None = None,
        enabled: bool = True,
    ) -> dict[str, Any]:
        if schedule_type not in {"once", "hourly", "daily", "weekly"}:
            raise ValueError("schedule_type must be one of: once, hourly, daily, weekly")

        now = self._now()
        requested_run = self._parse_datetime(run_at)
        if schedule_type == "once":
            next_run = requested_run or now
        else:
            if requested_run:
                next_run = requested_run
            else:
                next_run = self._next_run_after(schedule_type, interval_minutes, now)

        job_id = f"job_{uuid4().hex[:12]}"
        job = {
            "job_id": job_id,
            "project_id": project_id,
            "name": name,
            "job_type": job_type,
            "schedule_type": schedule_type,
            "interval_minutes": interval_minutes,
            "payload": payload or {},
            "enabled": enabled,
            "created_at": now.isoformat(),
            "next_run_at": next_run.isoformat() if next_run else None,
            "last_run_at": None,
            "run_count": 0,
        }

        self._jobs_by_project.setdefault(project_id, {})[job_id] = job
        if self._state_backend is not None:
            self._state_backend.upsert_workflow_job(job)
        return job

    def update_job(
        self,
        *,
        project_id: str,
        job_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        job = self._jobs_by_project.get(project_id, {}).get(job_id)
        if job is None and self._state_backend is not None:
            for persisted in self._state_backend.list_workflow_jobs(project_id=project_id):
                self._jobs_by_project.setdefault(project_id, {})[persisted["job_id"]] = persisted
            job = self._jobs_by_project.get(project_id, {}).get(job_id)
        if not job:
            raise ValueError(f"Unknown job_id: {job_id}")

        allowed_fields = {"name", "enabled", "interval_minutes", "payload", "next_run_at"}
        for key, value in updates.items():
            if key not in allowed_fields:
                raise ValueError(f"Unsupported update field: {key}")
            if key == "interval_minutes" and value is not None and int(value) <= 0:
                raise ValueError("interval_minutes must be positive")
            job[key] = value
        if "next_run_at" in updates and updates["next_run_at"]:
            parsed = self._parse_datetime(str(updates["next_run_at"]))
            job["next_run_at"] = parsed.isoformat() if parsed else None
        if self._state_backend is not None:
            self._state_backend.upsert_workflow_job(job)
        return job

    def delete_job(self, *, project_id: str, job_id: str) -> bool:
        project_jobs = self._jobs_by_project.get(project_id, {})
        removed = project_jobs.pop(job_id, None)
        if removed is not None:
            if self._state_backend is not None:
                self._state_backend.delete_workflow_job(project_id=project_id, job_id=job_id)
            return True

        if self._state_backend is not None:
            deleted = self._state_backend.delete_workflow_job(project_id=project_id, job_id=job_id)
            return bool(deleted)
        return False

    def list_jobs(self, project_id: str) -> list[dict[str, Any]]:
        if self._state_backend is not None and self.state_backend_mode == "postgres":
            return self._state_backend.list_workflow_jobs(project_id=project_id)
        jobs = list(self._jobs_by_project.get(project_id, {}).values())
        jobs.sort(key=lambda value: value.get("created_at", ""))
        return jobs

    def list_runs(self, project_id: str) -> list[dict[str, Any]]:
        if self._state_backend is not None and self.state_backend_mode == "postgres":
            return self._state_backend.list_workflow_runs(project_id=project_id)
        return self._runs_by_project.get(project_id, [])

    def list_reports(self, project_id: str) -> list[dict[str, Any]]:
        if self._state_backend is not None and self.state_backend_mode == "postgres":
            return self._state_backend.list_reports(project_id=project_id)
        return self._reports_by_project.get(project_id, [])

    def _store_run(self, project_id: str, run: dict[str, Any]) -> None:
        self._runs_by_project.setdefault(project_id, []).append(run)
        if self._state_backend is not None:
            self._state_backend.add_workflow_run(run)

    def _store_report(self, project_id: str, report: dict[str, Any]) -> None:
        self._reports_by_project.setdefault(project_id, []).append(report)
        if self._state_backend is not None:
            self._state_backend.add_report(report)

    def _execute_job(
        self,
        *,
        project_id: str,
        job: dict[str, Any],
        trigger: str,
        payload_override: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        merged_payload = dict(job.get("payload", {}))
        if payload_override:
            merged_payload.update(payload_override)

        if job["job_type"] == "weekly_status_report":
            report = self.generate_weekly_status_report(
                project_id=project_id,
                source=trigger,
                context={"job_id": job["job_id"], "job_name": job["name"], "payload": merged_payload},
            )
            return {
                "status": "completed",
                "job_type": job["job_type"],
                "report_id": report["report_id"],
                "summary": report["summary"],
            }

        if job["job_type"] == "audit_digest":
            runs = len(self._runs_by_project.get(project_id, []))
            return {
                "status": "completed",
                "job_type": "audit_digest",
                "summary": f"Audit digest created after {runs} workflow runs.",
            }

        return {
            "status": "completed",
            "job_type": job["job_type"],
            "summary": "Custom workflow executed.",
            "payload": merged_payload,
        }

    def run_job(
        self,
        *,
        project_id: str,
        job_id: str,
        trigger: str = "manual",
        payload_override: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        job = self._jobs_by_project.get(project_id, {}).get(job_id)
        if job is None and self._state_backend is not None:
            for persisted in self._state_backend.list_workflow_jobs(project_id=project_id):
                self._jobs_by_project.setdefault(project_id, {})[persisted["job_id"]] = persisted
            job = self._jobs_by_project.get(project_id, {}).get(job_id)
        if not job:
            raise ValueError(f"Unknown job_id: {job_id}")
        if not job.get("enabled", True):
            raise ValueError(f"Job {job_id} is disabled")

        now = self._now()
        result = self._execute_job(
            project_id=project_id,
            job=job,
            trigger=trigger,
            payload_override=payload_override,
        )
        job["last_run_at"] = now.isoformat()
        job["run_count"] = int(job.get("run_count", 0)) + 1
        if job["schedule_type"] == "once":
            job["enabled"] = False
            job["next_run_at"] = None
        else:
            next_run = self._next_run_after(
                job["schedule_type"],
                job.get("interval_minutes"),
                now,
            )
            job["next_run_at"] = next_run.isoformat() if next_run else None
        if self._state_backend is not None:
            self._state_backend.upsert_workflow_job(job)

        run = {
            "run_id": f"run_{uuid4().hex[:12]}",
            "project_id": project_id,
            "job_id": job_id,
            "trigger": trigger,
            "started_at": now.isoformat(),
            "result": result,
            "job_snapshot": {
                "name": job.get("name"),
                "job_type": job.get("job_type"),
                "schedule_type": job.get("schedule_type"),
            },
        }
        self._store_run(project_id, run)
        return run

    def run_due_jobs(self, *, project_id: str) -> list[dict[str, Any]]:
        now = self._now()
        due_runs: list[dict[str, Any]] = []
        for job in self.list_jobs(project_id):
            if not job.get("enabled", True):
                continue
            next_run_at = self._parse_datetime(job.get("next_run_at"))
            if next_run_at and next_run_at <= now:
                due_runs.append(
                    self.run_job(
                        project_id=project_id,
                        job_id=job["job_id"],
                        trigger="scheduled",
                    )
                )
        return due_runs

    def generate_weekly_status_report(
        self,
        *,
        project_id: str,
        source: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        generated_at = self._now_iso()
        report = {
            "report_id": f"report_{uuid4().hex[:12]}",
            "project_id": project_id,
            "type": "weekly_status",
            "generated_at": generated_at,
            "source": source,
            "summary": "Weekly status report generated.",
            "sections": [
                "Overall progress",
                "Completed milestones",
                "Open risks",
                "Next week priorities",
            ],
            "context": context or {},
        }
        self._store_report(project_id, report)
        return report
