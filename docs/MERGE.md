# Merging the ProjectForge AI sprint stack

This repository ships as a **stacked branch series** off `main`. Merge (or rebase-and-merge) in order so each PR builds on the previous one.

## Merge order

```
main
 └─ cursor/projectforge-v14-scaffold-dc5d          (Sprint 0)
     └─ cursor/sprint-1-langgraph-agents-dc5d      (Sprint 1)
         └─ cursor/sprint-2-persistence-dc5d       (Sprint 2)
             └─ cursor/sprint-3-oauth-flow-dc5d    (Sprint 3)
                 └─ cursor/sprint-4-project-graph-dc5d   (Sprint 4)
                     └─ cursor/sprint-5-temporal-dc5d   (Sprint 5)
                         └─ cursor/sprint-6-pdf-hardening-dc5d  (Sprint 6)
                             └─ cursor/sprint-7-auth-rbac-dc5d (Sprint 7)
                                 └─ cursor/sprint-8-locus-ompa-dc5d (Sprint 8)
                                     └─ cursor/sprint-9-deploy-manifests-dc5d (Sprint 9)
                                         └─ cursor/sprint-10-cad-bim-dc5d (Sprint 10)
                                             └─ cursor/sprint-11-repo-ingestion-dc5d (Sprint 11)
                                                 └─ cursor/sprint-12-frontend-dc5d (Sprint 12)
                                                     └─ cursor/sprint-13-integration-hardening-dc5d (Sprint 13)
                                                         └─ cursor/sprint-14-helm-frontend-e2e-dc5d (Sprint 14)
                                                             └─ cursor/sprint-15-ci-llm-playwright-dc5d (Sprint 15)
```

## Recommended workflow

1. Publish each draft PR from the GitHub UI (bottom of stack → top, or top-down if using merge queue).
2. Run CI on each PR (`backend` pytest + `frontend` build).
3. After Sprint 0 merges to `main`, retarget Sprint 1's base to `main` (or merge sequentially without retargeting if using merge commits).
4. Before production deploy, rotate secrets listed in `.env.example` (`ENCRYPTION_KEY`, `JWT_SECRET`, DB passwords).

## Full-stack smoke test (local)

```bash
cp .env.example .env
docker compose up -d --build
curl http://localhost:8000/health
curl http://localhost:3000/
open http://localhost:3000/projects
```

The frontend container proxies `/api/*` to the backend via `API_PROXY_TARGET` — no CORS configuration required for same-origin browser calls.

## Production

```bash
docker compose -f docker-compose.prod.yml up -d --build
# UI → http://localhost:3000   API → http://localhost:8000/health
```

See [deploy/README.md](deploy/README.md) for Helm and air-gapped installs.
