# On-prem deployment

Production overlay for air-gapped or self-hosted ProjectForge AI.

## Quick start

```bash
cp deploy/onprem/.env.prod.example .env
# Edit .env — set ENCRYPTION_KEY, Neo4j/Postgres passwords, OAuth credentials

docker compose -f docker-compose.yml -f deploy/onprem/docker-compose.prod.yml up -d
```

## What the overlay changes

| Setting | Value |
|---------|-------|
| `DEPLOYMENT_MODE` | `onprem` |
| `PROJECT_TIER` | `enterprise` (unlocks all feature gates) |
| `RBAC_ENFORCE` | `true` |
| `OAUTH_MOCK_TOKEN_EXCHANGE` | `false` |
| Backend | 2 uvicorn workers |
| Frontend | production build + `next start` |
| All services | `restart: unless-stopped` |

## RBAC in production

Pass actor context on API requests:

```http
X-ProjectForge-Actor: jane@company.com
X-ProjectForge-Role: editor
```

Assign project members:

```bash
curl -X POST http://localhost:8000/api/v1/projects/proj_123/access/members \
  -H "Content-Type: application/json" \
  -H "X-ProjectForge-Actor: admin" \
  -H "X-ProjectForge-Role: owner" \
  -d '{"actor_id":"jane@company.com","role":"editor"}'
```

## Native Locus + OMPA

Mount or install native packages and set `LOCUS_SOURCE_PATH` / `OMPA_SOURCE_PATH` in `.env`.

See [../../docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md) for system design.
