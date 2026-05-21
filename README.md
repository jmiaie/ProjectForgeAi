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
npm ci && npm run build && npm test
```

## Deployment

See [deploy/README.md](deploy/README.md). Profiles: `values-saas.yaml`, `values-hybrid.yaml`, `values-onprem.yaml`.

```bash
docker compose -f docker-compose.prod.yml up -d --build
helm upgrade --install projectforge ./deploy/helm/projectforge -f deploy/helm/projectforge/values-saas.yaml
```

## Ingestion

| Type | Parser | Notes |
| ---- | ------ | ----- |
| PDF | `PDFParser` | Chunking, tables, AcroForm, OCR fallback |
| DXF / IFC | `DXFParser`, `IFCParser` | Optional `ezdxf`, `ifcopenshell` |
| Repo zip/tar | `RepoArchiveParser` | Tree summary, manifests, README + source sample |

## Integrated sprints

| Sprint | Status |
| ------ | ------ |
| 1–8 | Done |
| 9 Deploy | Done (via sprint 11 branch) |
| 10 CAD/BIM | Done |
| 11 Repo ingestion | Done |

## License

Platform: proprietary. Forge CLI: MIT — see [LICENSE](LICENSE).
