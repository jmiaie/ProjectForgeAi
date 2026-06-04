# Merging the ProjectForge AI sprint stack

This repository ships as a **stacked branch series** off `main`. For v14 completion you may either merge the stack sequentially **or** merge the release branch directly.

## Fast path — v14 release branch

```bash
git checkout main
git merge origin/cursor/v14-complete-dc5d
```

This branch contains Sprints 0–18 (Phases 1–3). See [V14_COMPLETE.md](./V14_COMPLETE.md).

## Stacked merge order (historical)

```
main
 └─ cursor/projectforge-v14-scaffold-dc5d          (Sprint 0)
     └─ … (Sprints 1–14)
         └─ cursor/sprint-15-ci-llm-playwright-dc5d (Sprint 15)
             └─ cursor/v14-complete-dc5d             (Sprints 16–18 + release)
```

## Recommended workflow

1. Run CI: backend `pytest` + frontend `build` + `test:e2e`.
2. Merge `cursor/v14-complete-dc5d` → `main` (or merge the stack bottom-up).
3. Rotate secrets in `.env.example` before production (`ENCRYPTION_KEY`, `JWT_SECRET`).

## Full-stack smoke test (local)

```bash
cp .env.example .env
docker compose up -d --build
curl http://localhost:8000/api/v1/system/status
curl http://localhost:3000/
open http://localhost:3000/projects
```

See [deploy/README.md](../deploy/README.md) for Helm and air-gapped installs.
