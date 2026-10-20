# Roadmap: Forge GitHub App and Recipe Packs

**Updated:** 2026-10-20
**Product spec:** [PRD.md](PRD.md). **Current state:** [STATUS.md](STATUS.md). This roadmap follows STATUS.md's "Forge CLI golden path" and treats the backend "OS" as private scaffolding.

Rule: **no hosted offering of any kind ships before every P0 item below is closed.** Self-hosted use of the open-source CLI and App is unaffected.

---

## P0: Backend authorization (blocks any hosted offering)

### Done in this branch

- `validate_production_settings` now runs in `create_app()` (`backend/app/main.py`). With `APP_ENV=production`, the app refuses to start if any of these hold: `ALLOWED_ORIGINS` contains `*` (CORS always sends `allow_credentials=True`), the dev `JWT_SECRET` or `ENCRYPTION_KEY` is in use, or `AUTO_CREATE_SCHEMA=true`. Tests: `backend/tests/test_config_guardrails.py`.
- **Authentication** (401 without a valid bearer token) added to the routes below. Tests: `backend/tests/test_route_auth.py`.

| Route | File |
|---|---|
| `GET /api/v1/audit/` | `api/audit.py` (router-level) |
| `GET /api/v1/projects/` | `api/projects.py` `list_projects` |
| `GET /api/v1/projects/{project_id}` | `api/projects.py` `get_project` |
| `POST /api/v1/forge/runs` | `api/forge.py` `create_forge_run` |
| `GET /api/v1/forge/runs/{run_id}` | `api/forge.py` `get_forge_run` |
| `GET /api/v1/forge/runs?project_id=` | `api/forge.py` `list_forge_runs` |
| `POST /api/v1/projects/{project_id}/automations/` | `api/automations.py` (router-level) |
| `GET /api/v1/projects/{project_id}/automations/` | same |
| `GET /api/v1/projects/{project_id}/automations/{automation_id}` | same |
| `POST /api/v1/projects/{project_id}/automations/{automation_id}/run-now` | same |
| `DELETE /api/v1/projects/{project_id}/automations/{automation_id}` | same |
| `POST /api/v1/intake/connections` | `integrations/intake_form.py` `run_intake` |
| `GET /api/v1/intake/connections` | `integrations/intake_form.py` `list_connections` |
| `POST /api/v1/agents/orchestrate` | `api/agents.py` `orchestrate` |

These routes stay public on purpose because they return static catalogue data: `GET /api/v1/automations/kinds`, `GET /api/v1/agents/specialists`, `GET /api/v1/intake/connectors` and `GET /api/v1/intake/oauth/providers`.

### Still open (needs design decisions)

Authentication alone is **not** authorization. Any registered user (registration is open: `POST /api/v1/auth/register`) can still read and act on every organisation's data through the routes above.

| ID | Item | Exact routes | Decision needed |
|---|---|---|---|
| P0-1 | **Organisation scoping of project-bound routes.** Load the project, then require membership of `project.organization_id` with a role. `delete_project` in `api/projects.py` already does this inline; extract it into a dependency such as `require_project_role(Role.X)`. | All `/api/v1/projects/{project_id}/automations/*`; `GET /api/v1/projects/{project_id}`; `POST /api/v1/forge/runs` (body `project_id`); `GET /api/v1/forge/runs?project_id=`; `GET /api/v1/forge/runs/{run_id}` (via the run's project); `POST /api/v1/agents/orchestrate` (body `project_id`) | Minimum role per action (proposal: viewer reads; member creates, runs and runs-now; admin deletes). What happens to projects with `organization_id IS NULL`, which anonymous `POST /projects/` creates today? |
| P0-2 | **Scope list endpoints to the caller's organisations.** | `GET /api/v1/projects/` (returns all projects), `GET /api/v1/audit/` (returns all entries, including ones with `project_id = NULL`), `GET /api/v1/intake/connections` (calls `list_all()` when there is no `project_id`) | Should audit rows carry `organization_id`? This needs a migration. Who sees rows with no project? |
| P0-3 | **Routes that are still completely unauthenticated** (not covered by this branch) | `POST /api/v1/projects/` (anonymous create; runs the orchestrator, which costs LLM spend, when `objective` is set); `GET /api/v1/projects/{project_id}/graph/`, `/graph/stats`, `/graph/react-flow`, `/graph/nodes/{node_id}`, `/graph/schema` (`api/graph.py`); `POST /api/v1/projects/{project_id}/memory/retrieve`, `GET /memory/stats`, `GET` and `POST /memory/journal`, `POST /memory/sessions/start`, `POST /memory/sessions/{session_id}/end` (`api/memory.py`); `GET /api/v1/intake/oauth/{provider}/authorize` and `/callback` (`integrations/oauth/routes.py`; the callback persists connector credentials) | Should anonymous project creation be removed? The test `test_anonymous_project_creation_still_works_without_org_binding` pins it as a feature. How does the OAuth callback bind to an authenticated user and project? It is a browser redirect, so state must carry the user. |
| P0-4 | **LLM spend controls** on `POST /api/v1/agents/orchestrate`, `POST /api/v1/projects/` (with `objective`), and automation run-now | as listed | Per-org rate limits or budgets |
| P0-5 | **Deploy artifacts do not turn the guardrails on.** Neither `docker-compose.prod.yml` nor `deploy/helm/projectforge/templates/configmap.yaml` sets `APP_ENV=production`, and the Helm configmap defaults `ALLOWED_ORIGINS` to `"*"`. | n/a | Set `APP_ENV=production` in both, and require `backend.allowedOrigins` in Helm values. This breaks any existing deployment that runs on dev secrets, which is the intent, so the owner should schedule it. |
| P0-6 | **Groq default model.** `DEFAULT_LLM_MODEL` still defaults to `groq/llama-3.1-70b-versatile`, which Groq has retired. A current replacement could not be confirmed offline. It can be overridden with the `DEFAULT_LLM_MODEL` env var. | n/a | Choose a current Groq model, or switch the default provider. |

**P0 exit criteria:** every route under `/api/v1` except auth, health and the static catalogues requires authentication. Every project-, org- or connection-bound route enforces membership and role, with a test that a member of org A gets 403 or 404 on org B's resource. Prod deploy artifacts set `APP_ENV=production`.

---

## Now (0-30 days): GitHub App runs locally end-to-end

| ID | Deliverable | Exit criteria | Depends on |
|---|---|---|---|
| N1 | `github-app/` webhook scaffold. **Done in this branch.** | HMAC check (constant-time); 401 on unsigned or forged requests; `issues.labeled` with the configurable label is enqueued; the CLI is invoked via `execFileSync` with no shell; `app.yml` with minimal permissions; vitest coverage | none |
| N2 | **Open the draft PR** (replace the `openDraftPullRequest` stub in `github-app/src/forgeRunner.ts`) | App JWT → installation token; push `forge/issue-<n>`; `POST /repos/{owner}/{repo}/pulls` with `draft: true`; PR body links the issue and recipe@version; tested against recorded API responses | PRD Q4 (where output lands in the target repo) |
| N3 | Report failures back on the issue | A comment carries the CLI validation error | PRD Q5 (`issues: write`) |
| N4 | Idempotency and durability | Dedupe on `X-GitHub-Delivery`; jobs survive restart (file or SQLite queue) | N2 |
| N5 | Docs | `github-app/README.md` covering how to register from `app.yml`, plus env vars (`GITHUB_WEBHOOK_SECRET`, `FORGE_TRIGGER_LABEL`, `FORGE_CLI_PATH`, `PORT`, `WEBHOOK_PATH`) | N2 |

## Next (30-60 days): design partners, self-hosted

| ID | Deliverable | Exit criteria | Depends on |
|---|---|---|---|
| X1 | Self-hosted release of the App (container image) | Runs on one design partner's repo; draft PRs reviewed and merged | N1-N5 |
| X2 | Recipe pack format ADR (ADR-004) | Pack manifest, version pinning plus checksum, and how packs extend the schema `recipe` enum without breaking ADR-001's allowlist rule | PRD Q1 |
| X3 | First paid recipe pack (two or three recipes beyond `minimal` and `express-api`) | Passes the same `forge.test.ts`-style golden tests | X2 |

## Later (60-90 days): hosted

| ID | Deliverable | Exit criteria | Depends on |
|---|---|---|---|
| L1 | Pack install and licensing in the CLI (`forge pack add`) | Unlisted recipes are still refused; tested | X2, X3 |
| L2 | Per-job sandbox (container or firejail, per ADR-001 "Future") | Runs have no network and no host filesystem beyond the job dir | N4 |
| L3 | Hosted App | **All P0 closed**, L2 done, PRD metrics instrumented | P0, L2 |
