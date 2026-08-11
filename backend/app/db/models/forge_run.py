"""ForgeRun ORM model.

Represents a single Forge execution tied to a project.  The status field
follows a simple lifecycle: ``pending`` → ``running`` → ``completed`` |
``failed``.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class ForgeRun(Base, TimestampMixin):
    __tablename__ = "forge_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32), default="pending", nullable=False, index=True
    )
    recipe_id: Mapped[str] = mapped_column(String(128), nullable=False)
    recipe_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # The validated ForgeSpec that triggered this run, stored as JSON.
    spec: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    # Output manifest after a successful run.
    manifest: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # Human-readable error message when status == "failed".
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    project: Mapped[Project | None] = relationship(  # noqa: F821
        "Project", back_populates="forge_runs"
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "status": self.status,
            "recipe_id": self.recipe_id,
            "recipe_version": self.recipe_version,
            "spec": self.spec,
            "manifest": self.manifest,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
