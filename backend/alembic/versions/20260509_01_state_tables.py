"""Create state tables for compliance and workflows.

Revision ID: 20260509_01
Revises:
Create Date: 2026-05-09 23:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260509_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "compliance_profiles",
        sa.Column("project_id", sa.String(length=255), primary_key=True),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("last_updated", sa.String(length=64), nullable=False),
    )
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.String(length=64), nullable=False),
    )
    op.create_index("ix_audit_events_project_id", "audit_events", ["project_id"], unique=False)

    op.create_table(
        "workflow_jobs",
        sa.Column("job_id", sa.String(length=255), primary_key=True),
        sa.Column("project_id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("job_type", sa.String(length=128), nullable=False),
        sa.Column("schedule_type", sa.String(length=32), nullable=False),
        sa.Column("interval_minutes", sa.Integer(), nullable=True),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.String(length=64), nullable=False),
        sa.Column("next_run_at", sa.String(length=64), nullable=True),
        sa.Column("last_run_at", sa.String(length=64), nullable=True),
        sa.Column("run_count", sa.Integer(), nullable=False),
    )
    op.create_index("ix_workflow_jobs_project_id", "workflow_jobs", ["project_id"], unique=False)

    op.create_table(
        "workflow_runs",
        sa.Column("run_id", sa.String(length=255), primary_key=True),
        sa.Column("project_id", sa.String(length=255), nullable=False),
        sa.Column("job_id", sa.String(length=255), nullable=False),
        sa.Column("trigger", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.String(length=64), nullable=False),
        sa.Column("result", sa.Text(), nullable=False),
        sa.Column("job_snapshot", sa.Text(), nullable=False),
    )
    op.create_index("ix_workflow_runs_project_id", "workflow_runs", ["project_id"], unique=False)

    op.create_table(
        "workflow_reports",
        sa.Column("report_id", sa.String(length=255), primary_key=True),
        sa.Column("project_id", sa.String(length=255), nullable=False),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("generated_at", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("sections", sa.Text(), nullable=False),
        sa.Column("context", sa.Text(), nullable=False),
    )
    op.create_index("ix_workflow_reports_project_id", "workflow_reports", ["project_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_workflow_reports_project_id", table_name="workflow_reports")
    op.drop_table("workflow_reports")

    op.drop_index("ix_workflow_runs_project_id", table_name="workflow_runs")
    op.drop_table("workflow_runs")

    op.drop_index("ix_workflow_jobs_project_id", table_name="workflow_jobs")
    op.drop_table("workflow_jobs")

    op.drop_index("ix_audit_events_project_id", table_name="audit_events")
    op.drop_table("audit_events")

    op.drop_table("compliance_profiles")
