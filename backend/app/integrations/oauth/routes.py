"""HTTP routes wiring the real OAuth 2.0 / PKCE flow."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import AuditLogRepository, ConnectionRepository
from app.db.session import fastapi_get_session
from app.integrations.oauth.flow import OAuthFlow, OAuthFlowError
from app.integrations.oauth.providers import PROVIDERS

router = APIRouter(prefix="/intake/oauth", tags=["oauth"])


def _flow(session: AsyncSession) -> OAuthFlow:
    return OAuthFlow(session)


@router.get("/providers")
async def list_oauth_providers() -> dict[str, Any]:
    return {
        "providers": [
            {
                "name": name,
                "default_scopes": list(meta.default_scopes),
                "use_pkce": meta.use_pkce,
            }
            for name, meta in PROVIDERS.items()
        ]
    }


@router.get("/{provider}/authorize")
async def authorize(
    provider: str,
    project_id: str | None = Query(default=None),
    final_redirect: str | None = Query(default=None),
    scopes: str | None = Query(default=None, description="Comma-separated scopes"),
    redirect: bool = Query(default=False, description="If true, 302 to provider"),
    session: AsyncSession = Depends(fastapi_get_session),
) -> Any:
    flow = _flow(session)
    try:
        result = await flow.begin_authorize(
            provider,
            project_id=project_id,
            scopes=[s.strip() for s in scopes.split(",")] if scopes else None,
            final_redirect=final_redirect,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except OAuthFlowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    audit = AuditLogRepository(session)
    await audit.record(
        action="oauth.authorize_started",
        project_id=project_id,
        payload={"provider": provider, "state": result.state},
    )
    await session.commit()

    if redirect:
        return RedirectResponse(result.authorize_url, status_code=302)
    return {
        "provider": result.provider,
        "authorize_url": result.authorize_url,
        "state": result.state,
        "redirect_uri": result.redirect_uri,
    }


@router.get("/{provider}/callback")
async def callback(
    provider: str,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    error_description: str | None = Query(default=None),
    session: AsyncSession = Depends(fastapi_get_session),
) -> Any:
    if error:
        raise HTTPException(
            status_code=400,
            detail={"error": error, "error_description": error_description},
        )
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")

    flow = _flow(session)
    try:
        record = await flow.consume_state(state)
        if record.provider != provider:
            raise OAuthFlowError(
                f"State provider mismatch (expected {record.provider}, got {provider})"
            )
        token = await flow.exchange_code(
            provider=provider, code=code, state_record=record
        )
    except OAuthFlowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    secret_blob = json.dumps(
        {
            "access_token": token.access_token,
            "refresh_token": token.refresh_token,
            "token_type": token.token_type,
            "expires_in": token.expires_in,
            "scope": token.scope,
        }
    )

    connections = ConnectionRepository(session)
    audit = AuditLogRepository(session)
    record_db = await connections.create(
        connector_type=provider,
        auth_kind="oauth",
        provider=provider,
        project_id=record.project_id,
        scopes=(token.scope.split() if token.scope else []),
        secret=secret_blob,
        metadata=token.to_metadata(),
        status="connected",
    )
    await audit.record(
        action="oauth.connected",
        project_id=record.project_id,
        payload={
            "provider": provider,
            "connection_id": record_db.id,
            "expires_in": token.expires_in,
        },
    )
    await session.commit()

    if record.final_redirect:
        return RedirectResponse(record.final_redirect, status_code=302)
    return {
        "status": "connected",
        "provider": provider,
        "project_id": record.project_id,
        "connection_id": record_db.id,
        "metadata": token.to_metadata(),
    }
