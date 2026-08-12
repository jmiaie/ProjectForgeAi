"""Add forge_runs table.

Revision ID: 0005_forge_runs
Revises: 0004_auth_rbac
Create Date: 2026-08-11
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_forge_runs"
down_revision: str | None = "0004_auth_rbac"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "forge_runs",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(64),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("recipe_id", sa.String(128), nullable=False),
        sa.Column("recipe_version", sa.String(64), nullable=True),
        sa.Column("spec", sa.JSON(), nullable=False),
        sa.Column("manifest", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_forge_runs_project_id", "forge_runs", ["project_id"])
    op.create_index("ix_forge_runs_status", "forge_runs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_forge_runs_status", table_name="forge_runs")
    op.drop_index("ix_forge_runs_project_id", table_name="forge_runs")
    op.drop_table("forge_runs")
