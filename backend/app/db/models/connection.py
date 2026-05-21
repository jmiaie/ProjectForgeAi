"""Connection ORM model (third-party integrations).

Sensitive credentials are stored encrypted in ``encrypted_secret`` via the
``app.security.encryption`` helper. Plaintext secrets must never be persisted
in this column or in ``connection_metadata``.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Connection(Base, TimestampMixin):
    __tablename__ = "connections"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    connector_type: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    auth_kind: Mapped[str] = mapped_column(String(32), default="oauth", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="connected", nullable=False)
    scopes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    encrypted_secret: Mapped[str | None] = mapped_column(Text, nullable=True)
    connection_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, default=dict, nullable=False
    )

    project: Mapped["Project | None"] = relationship(  # noqa: F821
        "Project", back_populates="connections"
    )

    def to_dict(self, *, include_secret: bool = False) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.id,
            "project_id": self.project_id,
            "connector_type": self.connector_type,
            "provider": self.provider,
            "auth_kind": self.auth_kind,
            "status": self.status,
            "scopes": self.scopes,
            "metadata": self.connection_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_secret:
            payload["encrypted_secret"] = self.encrypted_secret
        return payload
