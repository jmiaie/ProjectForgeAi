"""Add oauth_states table.

Revision ID: 0002_oauth_states
Revises: 0001_initial
Create Date: 2026-05-09
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0002_oauth_states"
down_revision: str | Sequence[str] | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "oauth_states",
        sa.Column("state", sa.String(length=128), primary_key=True),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("code_verifier", sa.String(length=256), nullable=True),
        sa.Column("project_id", sa.String(length=64), nullable=True),
        sa.Column("redirect_uri", sa.String(length=512), nullable=False),
        sa.Column("final_redirect", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_oauth_states_provider", "oauth_states", ["provider"])
    op.create_index("ix_oauth_states_created_at", "oauth_states", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_oauth_states_created_at", table_name="oauth_states")
    op.drop_index("ix_oauth_states_provider", table_name="oauth_states")
    op.drop_table("oauth_states")
