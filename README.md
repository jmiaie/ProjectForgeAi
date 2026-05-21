# ProjectForge AI

> **Universal Agentic Project Management OS in a Box.**

Master Build Framework v14 + **Forge CLI**.

## Highlights

- LangGraph orchestrator + specialist agents
- Postgres + Alembic, OAuth, JWT + RBAC
- Locus + OMPA memory APIs
- Project graph, automations
- **Ingestion** — PDF (tables/OCR), CAD/BIM (DXF/IFC), repo archives (zip/tar)
- **Deploy** — Helm (SaaS/hybrid/on-prem) + production Docker Compose
- Forge CLI + REST API

## Quick start (dev)

```bash
cp .env.example .env && docker-compose up -d
cd backend && pip install -r requirements.txt && python -m alembic upgrade head
uvicorn app.main:app --reload
```

```bash
cd frontend && npm install && npm run dev
npm ci && npm run build && npm test   # Forge CLI (repo root)
```

## Deployment

See [deploy/README.md](deploy/README.md).

```bash
docker compose -f docker-compose.prod.yml up -d --build
helm upgrade --install projectforge ./deploy/helm/projectforge \
  -f deploy/helm/projectforge/values-saas.yaml
```

## Ingestion

| Type | Parser |
| ---- | ------ |
| PDF | `PDFParser` — chunking, tables, AcroForm, OCR |
| DXF / IFC | `DXFParser`, `IFCParser` |
| Repo archive | `RepoArchiveParser` — zip/tar/tgz snapshots |

## Integrated sprints (all merged)

| # | Focus |
| - | ----- |
| 1 | LangGraph + specialists |
| 2 | Postgres + Alembic |
| 3 | OAuth 2.0 / PKCE |
| 4 | Project graph |
| 5 | Automations |
| 6 | PDF hardening |
| 7 | Auth + RBAC |
| 8 | Locus + OMPA |
| 9 | Deploy manifests (Helm / on-prem) |
| 10 | CAD / BIM |
| 11 | Repo ingestion |

## License

Platform: proprietary. Forge CLI: MIT — see [LICENSE](LICENSE).
