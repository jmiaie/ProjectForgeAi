"""Add automations table.

Revision ID: 0003_automations
Revises: 0002_oauth_states
Create Date: 2026-05-09
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0003_automations"
down_revision: str | Sequence[str] | None = "0002_oauth_states"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "automations",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(length=64),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("interval_seconds", sa.Integer(), nullable=True),
        sa.Column("cron", sa.String(length=128), nullable=True),
        sa.Column("max_runs", sa.Integer(), nullable=True),
        sa.Column("runs_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("workflow_handle", sa.String(length=128), nullable=True),
        sa.Column("config", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_automations_project_id", "automations", ["project_id"])
    op.create_index("ix_automations_status", "automations", ["status"])
    op.create_index("ix_automations_next_run_at", "automations", ["next_run_at"])


def downgrade() -> None:
    op.drop_index("ix_automations_next_run_at", table_name="automations")
    op.drop_index("ix_automations_status", table_name="automations")
    op.drop_index("ix_automations_project_id", table_name="automations")
    op.drop_table("automations")
