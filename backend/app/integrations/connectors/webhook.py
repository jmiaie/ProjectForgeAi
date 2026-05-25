import hashlib
import hmac
import json
import secrets

import httpx


class WebhookConnector:
    def __init__(self, name: str = "webhook", config: dict | None = None):
        self.name = name
        self.config = config or {}

    async def authenticate(self, auth_data: dict):
        webhook_url = auth_data.get("webhook_url")
        if not webhook_url:
            raise ValueError("webhook requires webhook_url")

        secret = auth_data.get("secret") or secrets.token_urlsafe(32)
        events = auth_data.get("events") or ["project.updated", "automation.completed"]
        delivery_mode = auth_data.get("delivery_mode", "json")

        return {
            "id": f"webhook_{hashlib.sha256(webhook_url.encode()).hexdigest()[:12]}",
            "webhook_url": webhook_url,
            "secret": secret,
            "events": events,
            "delivery_mode": delivery_mode,
            "signing_algorithm": "hmac-sha256",
        }

    async def deliver_test(self, connection: dict) -> dict:
        payload = {"event": "webhook.test", "status": "ok"}
        return await self._post_event(connection, payload)

    async def health(self, connection: dict | None = None) -> dict:
        if not connection:
            return {
                "connector": self.name,
                "status": "not_connected",
                "checks": {"webhook_url_present": False},
            }

        webhook_url = connection.get("webhook_url")
        reachable = False
        if webhook_url:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.head(webhook_url)
                    reachable = response.status_code < 500
            except httpx.HTTPError:
                reachable = False

        return {
            "connector": self.name,
            "status": "connected",
            "checks": {
                "webhook_url_present": bool(webhook_url),
                "secret_present": bool(connection.get("secret")),
                "event_count": len(connection.get("events", [])),
                "endpoint_reachable": reachable,
            },
        }

    async def _post_event(self, connection: dict, payload: dict) -> dict:
        webhook_url = connection["webhook_url"]
        body = json.dumps(payload)
        headers = {"Content-Type": "application/json"}
        secret = connection.get("secret")
        if secret:
            signature = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
            headers["X-ProjectForge-Signature"] = f"sha256={signature}"

        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.post(webhook_url, content=body, headers=headers)
            return {
                "status_code": response.status_code,
                "delivered": response.status_code < 400,
            }
