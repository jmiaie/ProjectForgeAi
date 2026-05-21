"""OAuth in-flight state tracking.

Stores the ``state`` token, PKCE verifier, target provider, optional
project_id, and the redirect URI so the callback can validate and exchange
without trusting the client. Rows are short-lived (TTL via
``OAUTH_STATE_TTL_SECONDS``) and are deleted once consumed.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class OAuthState(Base):
    __tablename__ = "oauth_states"

    state: Mapped[str] = mapped_column(String(128), primary_key=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    code_verifier: Mapped[str | None] = mapped_column(String(256), nullable=True)
    project_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    redirect_uri: Mapped[str] = mapped_column(String(512), nullable=False)
    final_redirect: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    def is_expired(self, ttl_seconds: int) -> bool:
        created = self.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - created).total_seconds()
        return age > ttl_seconds
