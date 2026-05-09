from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from app.core.config import Settings

try:
    from sqlalchemy import (
        Boolean,
        Column,
        Integer,
        MetaData,
        String,
        Table,
        Text,
        and_,
        create_engine,
        select,
    )
except ImportError:  # pragma: no cover - handled at runtime
    Boolean = Column = Integer = MetaData = String = Table = Text = None  # type: ignore
    and_ = create_engine = select = None  # type: ignore


metadata = MetaData() if MetaData else None

compliance_profiles = (
    Table(
        "compliance_profiles",
        metadata,
        Column("project_id", String(255), primary_key=True),
        Column("category", String(64), nullable=False),
        Column("last_updated", String(64), nullable=False),
    )
    if metadata is not None
    else None
)

audit_events = (
    Table(
        "audit_events",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("project_id", String(255), nullable=False, index=True),
        Column("event_type", String(128), nullable=False),
        Column("payload", Text, nullable=False),
        Column("timestamp", String(64), nullable=False),
    )
    if metadata is not None
    else None
)

workflow_jobs = (
    Table(
        "workflow_jobs",
        metadata,
        Column("job_id", String(255), primary_key=True),
        Column("project_id", String(255), nullable=False, index=True),
        Column("name", String(255), nullable=False),
        Column("job_type", String(128), nullable=False),
        Column("schedule_type", String(32), nullable=False),
        Column("interval_minutes", Integer, nullable=True),
        Column("payload", Text, nullable=False),
        Column("enabled", Boolean, nullable=False),
        Column("created_at", String(64), nullable=False),
        Column("next_run_at", String(64), nullable=True),
        Column("last_run_at", String(64), nullable=True),
        Column("run_count", Integer, nullable=False),
    )
    if metadata is not None
    else None
)

workflow_runs = (
    Table(
        "workflow_runs",
        metadata,
        Column("run_id", String(255), primary_key=True),
        Column("project_id", String(255), nullable=False, index=True),
        Column("job_id", String(255), nullable=False),
        Column("trigger", String(32), nullable=False),
        Column("started_at", String(64), nullable=False),
        Column("result", Text, nullable=False),
        Column("job_snapshot", Text, nullable=False),
    )
    if metadata is not None
    else None
)

workflow_reports = (
    Table(
        "workflow_reports",
        metadata,
        Column("report_id", String(255), primary_key=True),
        Column("project_id", String(255), nullable=False, index=True),
        Column("type", String(64), nullable=False),
        Column("generated_at", String(64), nullable=False),
        Column("source", String(64), nullable=False),
        Column("summary", Text, nullable=False),
        Column("sections", Text, nullable=False),
        Column("context", Text, nullable=False),
    )
    if metadata is not None
    else None
)


class PostgresStateStore:
    """State repository for compliance/audit/workflow with Postgres fallback."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._engine = None
        self._mode = "in_memory"

        self._profiles_memory: dict[str, dict[str, Any]] = {}
        self._audit_memory: list[dict[str, Any]] = []
        self._jobs_memory: dict[str, dict[str, dict[str, Any]]] = {}
        self._runs_memory: dict[str, list[dict[str, Any]]] = {}
        self._reports_memory: dict[str, list[dict[str, Any]]] = {}

        self._init_engine()

    @property
    def backend_mode(self) -> str:
        return self._mode

    def _init_engine(self) -> None:
        if create_engine is None or metadata is None:
            self._mode = "in_memory"
            return
        try:
            engine = create_engine(self._settings.POSTGRES_URI, pool_pre_ping=True)
            with engine.connect():
                pass
            metadata.create_all(engine)
            self._engine = engine
            self._mode = "postgres"
        except Exception:
            self._engine = None
            self._mode = "in_memory"

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(UTC).isoformat()

    @staticmethod
    def _json_load(value: str) -> Any:
        return json.loads(value) if value else {}

    @staticmethod
    def _json_dump(value: Any) -> str:
        return json.dumps(value, separators=(",", ":"), sort_keys=True)

    def _execute(self, statement):
        if self._engine is None:
            raise RuntimeError("Postgres engine not available")
        with self._engine.begin() as connection:
            connection.execute(statement)

    def _fetch_one(self, statement):
        if self._engine is None:
            raise RuntimeError("Postgres engine not available")
        with self._engine.begin() as connection:
            return connection.execute(statement).mappings().first()

    def _fetch_all(self, statement):
        if self._engine is None:
            raise RuntimeError("Postgres engine not available")
        with self._engine.begin() as connection:
            return connection.execute(statement).mappings().all()

    # Compliance profile persistence
    def upsert_compliance_profile(self, project_id: str, category: str, last_updated: str) -> dict[str, Any]:
        profile = {"project_id": project_id, "category": category, "last_updated": last_updated}
        if self._mode != "postgres" or compliance_profiles is None:
            self._profiles_memory[project_id] = profile
            return profile

        existing = self._fetch_one(
            select(compliance_profiles.c.project_id).where(compliance_profiles.c.project_id == project_id)
        )
        if existing:
            self._execute(
                compliance_profiles.update()
                .where(compliance_profiles.c.project_id == project_id)
                .values(category=category, last_updated=last_updated)
            )
        else:
            self._execute(compliance_profiles.insert().values(**profile))
        return profile

    def get_compliance_profile(self, project_id: str) -> dict[str, Any] | None:
        if self._mode != "postgres" or compliance_profiles is None:
            return self._profiles_memory.get(project_id)
        row = self._fetch_one(
            select(compliance_profiles).where(compliance_profiles.c.project_id == project_id)
        )
        return dict(row) if row else None

    # Audit persistence
    def add_audit_event(self, event: dict[str, Any]) -> dict[str, Any]:
        if self._mode != "postgres" or audit_events is None:
            self._audit_memory.append(event)
            return event
        self._execute(
            audit_events.insert().values(
                project_id=event["project_id"],
                event_type=event["event_type"],
                payload=self._json_dump(event["payload"]),
                timestamp=event["timestamp"],
            )
        )
        return event

    def list_audit_events(self, project_id: str, limit: int = 100) -> list[dict[str, Any]]:
        if self._mode != "postgres" or audit_events is None:
            events = [event for event in self._audit_memory if event["project_id"] == project_id]
            return events[-limit:]

        rows = self._fetch_all(
            select(audit_events)
            .where(audit_events.c.project_id == project_id)
            .order_by(audit_events.c.timestamp.asc())
        )
        parsed = [
            {
                "project_id": row["project_id"],
                "event_type": row["event_type"],
                "payload": self._json_load(row["payload"]),
                "timestamp": row["timestamp"],
            }
            for row in rows
        ]
        return parsed[-limit:]

    # Workflow job persistence
    def upsert_workflow_job(self, job: dict[str, Any]) -> dict[str, Any]:
        project_id = job["project_id"]
        job_id = job["job_id"]
        if self._mode != "postgres" or workflow_jobs is None:
            self._jobs_memory.setdefault(project_id, {})[job_id] = dict(job)
            return job

        existing = self._fetch_one(select(workflow_jobs.c.job_id).where(workflow_jobs.c.job_id == job_id))
        payload = {
            "project_id": project_id,
            "name": job["name"],
            "job_type": job["job_type"],
            "schedule_type": job["schedule_type"],
            "interval_minutes": job.get("interval_minutes"),
            "payload": self._json_dump(job.get("payload", {})),
            "enabled": bool(job.get("enabled", True)),
            "created_at": job["created_at"],
            "next_run_at": job.get("next_run_at"),
            "last_run_at": job.get("last_run_at"),
            "run_count": int(job.get("run_count", 0)),
        }
        if existing:
            self._execute(workflow_jobs.update().where(workflow_jobs.c.job_id == job_id).values(**payload))
        else:
            self._execute(workflow_jobs.insert().values(job_id=job_id, **payload))
        return job

    def list_workflow_jobs(self, project_id: str) -> list[dict[str, Any]]:
        if self._mode != "postgres" or workflow_jobs is None:
            jobs = list(self._jobs_memory.get(project_id, {}).values())
            jobs.sort(key=lambda value: value.get("created_at", ""))
            return jobs

        rows = self._fetch_all(
            select(workflow_jobs)
            .where(workflow_jobs.c.project_id == project_id)
            .order_by(workflow_jobs.c.created_at.asc())
        )
        return [
            {
                "job_id": row["job_id"],
                "project_id": row["project_id"],
                "name": row["name"],
                "job_type": row["job_type"],
                "schedule_type": row["schedule_type"],
                "interval_minutes": row["interval_minutes"],
                "payload": self._json_load(row["payload"]),
                "enabled": bool(row["enabled"]),
                "created_at": row["created_at"],
                "next_run_at": row["next_run_at"],
                "last_run_at": row["last_run_at"],
                "run_count": int(row["run_count"]),
            }
            for row in rows
        ]

    def delete_workflow_job(self, project_id: str, job_id: str) -> bool:
        if self._mode != "postgres" or workflow_jobs is None:
            project_jobs = self._jobs_memory.get(project_id, {})
            return project_jobs.pop(job_id, None) is not None

        row = self._fetch_one(
            select(workflow_jobs.c.job_id).where(
                and_(workflow_jobs.c.project_id == project_id, workflow_jobs.c.job_id == job_id)
            )
        )
        if not row:
            return False
        self._execute(
            workflow_jobs.delete().where(
                and_(workflow_jobs.c.project_id == project_id, workflow_jobs.c.job_id == job_id)
            )
        )
        return True

    def add_workflow_run(self, run: dict[str, Any]) -> dict[str, Any]:
        project_id = run["project_id"]
        if self._mode != "postgres" or workflow_runs is None:
            self._runs_memory.setdefault(project_id, []).append(dict(run))
            return run

        self._execute(
            workflow_runs.insert().values(
                run_id=run["run_id"],
                project_id=project_id,
                job_id=run["job_id"],
                trigger=run["trigger"],
                started_at=run["started_at"],
                result=self._json_dump(run["result"]),
                job_snapshot=self._json_dump(run["job_snapshot"]),
            )
        )
        return run

    def list_workflow_runs(self, project_id: str) -> list[dict[str, Any]]:
        if self._mode != "postgres" or workflow_runs is None:
            return self._runs_memory.get(project_id, [])

        rows = self._fetch_all(
            select(workflow_runs)
            .where(workflow_runs.c.project_id == project_id)
            .order_by(workflow_runs.c.started_at.asc())
        )
        return [
            {
                "run_id": row["run_id"],
                "project_id": row["project_id"],
                "job_id": row["job_id"],
                "trigger": row["trigger"],
                "started_at": row["started_at"],
                "result": self._json_load(row["result"]),
                "job_snapshot": self._json_load(row["job_snapshot"]),
            }
            for row in rows
        ]

    def add_report(self, report: dict[str, Any]) -> dict[str, Any]:
        project_id = report["project_id"]
        if self._mode != "postgres" or workflow_reports is None:
            self._reports_memory.setdefault(project_id, []).append(dict(report))
            return report

        self._execute(
            workflow_reports.insert().values(
                report_id=report["report_id"],
                project_id=project_id,
                type=report["type"],
                generated_at=report["generated_at"],
                source=report["source"],
                summary=report["summary"],
                sections=self._json_dump(report.get("sections", [])),
                context=self._json_dump(report.get("context", {})),
            )
        )
        return report

    def list_reports(self, project_id: str) -> list[dict[str, Any]]:
        if self._mode != "postgres" or workflow_reports is None:
            return self._reports_memory.get(project_id, [])

        rows = self._fetch_all(
            select(workflow_reports)
            .where(workflow_reports.c.project_id == project_id)
            .order_by(workflow_reports.c.generated_at.asc())
        )
        return [
            {
                "report_id": row["report_id"],
                "project_id": row["project_id"],
                "type": row["type"],
                "generated_at": row["generated_at"],
                "source": row["source"],
                "summary": row["summary"],
                "sections": self._json_load(row["sections"]),
                "context": self._json_load(row["context"]),
            }
            for row in rows
        ]
