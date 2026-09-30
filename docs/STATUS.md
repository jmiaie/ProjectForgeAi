# Status — ProjectForgeAi

**Updated:** 2026-09-30 (PT)  
**Maturity:** **WIP / partial MVP** — Forge CLI path is the credible core; “Universal Agentic PM OS” is aspirational scaffolding around it.

## Honest split

| Layer | State | Evidence |
|-------|--------|----------|
| **Forge CLI** (`src/`, recipes `minimal` / `express-api`) | **MVP-ish** | `forge validate` / `forge run` / `forge publish`; vitest in-repo; examples under `examples/specs/` |
| FastAPI backend + alembic + many specialist tests | Scaffold / in-progress platform | Large `backend/tests/` surface; needs Postgres/stack for full runs |
| Frontend intake / React Flow | Present | Requires `npm` + env; not claimed verified in this pass |
| Helm / `docker-compose.prod.yml` | Deploy artifacts | Not a proof of production traffic |

## What to demo (15 minutes)

1. `npm ci && npm run build && npm test` (Forge unit/smoke)
2. `npm run forge -- validate --spec ./examples/specs/api-service.json`
3. `npm run forge -- run --spec ./examples/specs/api-service.json --output /tmp/forge-api-out`
4. Show `forge.manifest.json` + generated tree; **stop before** `--push` unless reviewing a real draft PR target

Optional (heavier): `docker compose up` backend/frontend only if Jeff wants full OS pitch — treat failures as environment setup, not as Forge CLI regressions.

## Non-claims

- Not a hosted multi-tenant PM product
- Not “every integration” (Neo4j graph, CAD/PDF ingestion, OAuth) proven end-to-end on every clone
- Open PR [#6](https://github.com/jmiaie/ProjectForgeAi/pull/6) (`qa/forge-git-identity`) left for Jeff — CI git identity; may touch workflows

## Next actions

1. Trim pitch to **Forge CLI golden path** until backend e2e is routinely green offline
2. One recorded demo script (commands above) for agentic-PM conversations
3. Decide whether backend “OS” stays in-tree or splits later — out of scope for this hygiene PR
