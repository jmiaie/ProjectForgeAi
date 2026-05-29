# ProjectForge AI — Deployment Guide

Three deployment profiles ship with this repository:

| Profile | File | Use case |
| ------- | ---- | -------- |
| **SaaS** | `values-saas.yaml` | Multi-tenant cloud: ingress + HPA + managed secrets |
| **Hybrid** | `values-hybrid.yaml` | External managed Postgres/Redis, in-cluster Neo4j + API |
| **On-prem / air-gapped** | `values-onprem.yaml` | Single-tenant, local registry, no outbound pulls |

## Quick start (Docker Compose — production)

```bash
cp .env.example .env
# Edit secrets: ENCRYPTION_KEY, JWT_SECRET, POSTGRES_PASSWORD, NEO4J_PASSWORD

docker compose -f docker-compose.prod.yml up -d --build
curl http://localhost:8000/health
curl http://localhost:3000/
```

The production compose file runs Alembic migrations automatically via the backend entrypoint before starting Uvicorn.

## Kubernetes (Helm)

```bash
# Dev / staging (bundled Postgres + Redis + Neo4j)
helm upgrade --install projectforge ./deploy/helm/projectforge \
  --namespace projectforge --create-namespace \
  --set secrets.encryptionKey="$(openssl rand -hex 32)" \
  --set secrets.jwtSecret="$(openssl rand -hex 48)"

# SaaS profile
helm upgrade --install projectforge ./deploy/helm/projectforge \
  -f deploy/helm/projectforge/values-saas.yaml \
  --set secrets.encryptionKey=... --set secrets.jwtSecret=...

# Hybrid (external database)
helm upgrade --install projectforge ./deploy/helm/projectforge \
  -f deploy/helm/projectforge/values-hybrid.yaml \
  --set backend.externalDatabaseUrl='postgresql+asyncpg://user:pass@rds-host:5432/projectforge'
```

### What the chart deploys

- **Backend** Deployment with liveness/readiness probes on `/health`, PVC for Locus/OMPA/graph data
- **Frontend** Deployment (Next.js UI) with probes on `/`, optional HPA
- **Ingress** routes `/api/*` to the backend and `/` to the frontend (same-origin browser calls)
- **Alembic migration** Job (Helm post-install/post-upgrade hook)
- **PostgreSQL** StatefulSet (optional — disable for hybrid)
- **Redis** Deployment (optional)
- **Neo4j** StatefulSet (optional — enable for graph backend)
- **Ingress** (optional)
- **HPA** (SaaS profile)

## Air-gapped / on-prem install

On a connected build machine:

```bash
chmod +x deploy/onprem/*.sh
./deploy/onprem/bundle-images.sh
# Transfer deploy/onprem/bundles/projectforge-images-*.tar to the target host
```

On the air-gapped host:

```bash
./deploy/onprem/load-images.sh deploy/onprem/bundles/projectforge-images-0.14.0.tar
./deploy/onprem/install.sh \
  --set global.imageRegistry=registry.local/projectforge \
  --set secrets.encryptionKey=... \
  --set secrets.jwtSecret=...
```

## Environment variables

See `.env.example` for the full list. Production installs **must** set:

- `ENCRYPTION_KEY` — Fernet key derivation secret (rotate on schedule)
- `JWT_SECRET` — JWT signing secret
- `DATABASE_URL` — async SQLAlchemy URL (`postgresql+asyncpg://...`)
- `AUTO_CREATE_SCHEMA=false` — rely on Alembic migrations in production

## Migrations

```bash
# Local / CI
cd backend && python -m alembic upgrade head

# Kubernetes (automatic via Helm hook + entrypoint)
# Manual one-off:
kubectl run pf-migrate --rm -it --restart=Never \
  --image=projectforge-ai/backend:0.14.0 \
  --env-from=configmap/projectforge-config \
  -- python3 -m alembic upgrade head
```

## Health checks

- `GET /health` — liveness + readiness (used by K8s probes and Docker healthcheck)
