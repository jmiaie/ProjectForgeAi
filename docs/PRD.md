# PRD: Forge GitHub App and Recipe Packs

**Status:** Draft for owner review
**Updated:** 2026-10-20
**Scope:** the Forge CLI (`src/`, `templates/`, `schemas/`) packaged as (a) a GitHub App and (b) paid recipe packs.
**Out of scope:** the PM-OS FastAPI backend (`backend/app`). It stays private and is not sold until the P0 authorization work in [ROADMAP.md](ROADMAP.md) is done.

Every statement about current behaviour below points at code in this repository. Anything not yet built is marked **(planned)**; guesses are marked **(assumption)**. There are no customers, usage numbers or market figures in this document because the repository has none.

Related: [STATUS.md](STATUS.md), [vision.md](vision.md), [ADR-001](adr/001-execution-model.md), [ADR-002](adr/002-spec-planner.md), [ADR-003](adr/003-forge-publish.md).

---

## 1. Problem

Starting a new service or repo from a spec takes manual copying of boilerplate, and the result often skips review. ProjectForgeAi already has a credible core for this. [STATUS.md](STATUS.md) calls the Forge CLI "the credible core":

- `forge validate --spec` checks a JSON spec against `schemas/forge-spec.schema.json` (`src/planner.ts`).
- `forge run --spec | --recipe` renders an allowlisted recipe into an empty directory, refuses path traversal and unresolved `{{vars}}`, and writes `forge.manifest.json` (`src/forge.ts`).
- `forge publish` commits the output on a `forge/...` branch, never `main`, and can open a **draft** PR with the `gh` CLI if it is installed (`src/publish.ts`, ADR-003). Git runs through `execFileSync` with argument arrays, with no shell.

What is missing is the step teams use every day: going from an issue to a reviewable PR without someone running the CLI locally. ADR-001 already lists "GitHub App with least-privilege scopes for PR creation only" as future work.

## 2. Target users (assumptions to validate)

| Segment | Why they might care | Evidence in repo |
|---|---|---|
| Platform / DevEx engineers who own service templates | Want templates applied consistently, through review | Recipes are versioned (`recipe.json`, `src/recipes/index.ts`) |
| Small teams without a platform team | Want a working starter (CI stub, health route) from a short spec | `templates/express-api`, `templates/minimal` |
| Agencies / consultancies that start many similar repos | Repeatable output plus an audit trail | `forge.manifest.json` per run |

**(assumption)** None of these segments have been interviewed. Section 11 lists the validation questions.

## 3. Jobs to be done

1. "When I've written down what a new service needs, I want a reviewed PR with a working skeleton, so I don't hand-copy boilerplate."
2. "When I approve a template, I want every new project to use that exact version, so drift is visible."
3. "When generated code lands, I want it to go through normal review, so nothing reaches `main` unreviewed."

## 4. Product

### 4a. Forge GitHub App

**Flow:** someone opens an issue whose body contains a fenced ```` ```json ```` Forge spec. A maintainer adds the trigger label (default `forge`, configurable). The App verifies the webhook, runs `forge run` and `forge publish` (local commit), and opens a **draft** PR linked to the issue **(the PR step is planned)**.

Built in this PR (`github-app/`):

- Webhook server on Node's `http` module, with no new dependencies (`github-app/src/server.ts`).
- `X-Hub-Signature-256` HMAC-SHA256 check with `crypto.timingSafeEqual`. Unsigned or wrongly signed requests get 401 before the body is parsed (`signature.ts`).
- Routing: only `issues` + `labeled` + the trigger label is enqueued. Everything else gets 200 and is ignored (`router.ts`).
- In-process FIFO queue, one job at a time (`queue.ts`).
- Runner: pulls the spec out of the issue body, writes it to a fresh `mkdtemp` directory, and calls the existing CLI with `execFileSync(process.execPath, [cli, "run", ...])`, with no shell. This is the same pattern `src/publish.ts` uses for git (`forgeRunner.ts`).
- `openDraftPullRequest` is a stub that throws `NotImplementedError` and points to ROADMAP N2.
- `github-app/app.yml` manifest asking for `metadata:read`, `issues:read`, `contents:write` and `pull_requests:write`.

### 4b. Recipe packs

A recipe is a directory under `templates/<id>/` registered in `src/recipes/index.ts` and listed in the schema's `recipe` enum (ADR-002). Today there are two: `minimal@1.0.0` and `express-api@1.0.0`. A **recipe pack** is a versioned set of extra recipes plus their schema fields **(planned)**.

The CLI only runs allowlisted recipes from inside the repo (ADR-001 rule 3). Shipping packs separately therefore needs a pack format and a loading mechanism that keeps that rule, for example signed or checksummed packs pinned in a lockfile **(planned, needs an ADR)**.

## 5. Goals and non-goals

**Goals**
- G1. Labelled issue to draft PR on a repo where the App is installed, with no local CLI.
- G2. Generated code is never pushed to the default branch and always arrives as a draft PR (ADR-001, ADR-003).
- G3. Least-privilege App permissions, as listed in `app.yml`.
- G4. Recipe packs extend the allowlist without allowing arbitrary template URLs (ADR-001 rejects these).

**Non-goals**
- Selling or hosting the PM-OS backend (`backend/app`).
- LLM-generated code in PRs. Today's recipes are deterministic templates, and ADR-002 lists an LLM planner only as future work.
- Auto-merge, or any write to the default branch.
- Running recipe hooks or arbitrary shell commands from specs (ADR-001 "Full shell access from specs" is rejected).

## 6. User stories and acceptance criteria

| # | Story | Acceptance criteria | State |
|---|---|---|---|
| US1 | As a maintainer, I label an issue `forge` and get a draft PR. | Given a spec block that passes the schema, labelling the issue starts a run. A draft PR from `forge/issue-<n>` is opened against the default branch, and its body links the issue and names the recipe and version from `forge.manifest.json`. | Run + local publish built; PR **planned (N2)** |
| US2 | As a maintainer, I can't be spoofed. | A request without a valid `X-Hub-Signature-256` for the configured secret gets 401 and does not enqueue a job. The server will not start without `GITHUB_WEBHOOK_SECRET`. | Built, tested |
| US3 | As an admin, I choose the trigger label. | `FORGE_TRIGGER_LABEL` changes the label. Other labels and `unlabeled` are ignored. | Built, tested |
| US4 | As a spec author, I see why a run failed. | An invalid spec (bad JSON, schema violation, no block) gives a comment on the issue with the CLI's validation message. | Rejection built; comment **planned (N3)**, needs `issues: write` |
| US5 | As a security reviewer, I can verify nothing from the issue reaches a shell or an arbitrary path. | The CLI is invoked with `execFileSync` and an args array with `shell: false`. Spec and output paths are under a per-job `mkdtemp` directory. The branch name is built from the numeric issue number only. | Built, tested |
| US6 | As a buyer of a recipe pack, I install it and its recipes show up in `forge list`. | The pack is pinned by version and checksum, and `forge validate` accepts its recipe ids. Recipes outside installed packs are still refused. | **Planned (L1)** |

## 7. Functional requirements

- FR1. Verify the HMAC on the raw body before parsing. Reject when the header is missing, malformed, or uses `sha1=` (built).
- FR2. Respond within GitHub's webhook timeout. The run happens after the 202 (built: the in-process queue).
- FR3. Spec source is the first ```` ```json ```` block in the issue body, at most 10,000 characters. The CLI runs the schema validation (built).
- FR4. One run per labelled delivery. Re-labelling starts a new run **(planned: dedupe on `X-GitHub-Delivery`, N4)**.
- FR5. Draft PR only, from a `forge/` branch (ADR-003) **(planned, N2)**.
- FR6. Authenticate as the installation, using an App JWT exchanged for an installation token. No personal tokens **(planned, N2)**.

## 8. Non-functional requirements

- Security: constant-time signature comparison. No shell. The webhook secret and App private key are stripped from the CLI child's environment (built). The App private key is loaded only from the environment or a secret store **(planned)**.
- Reliability: jobs are lost on restart today. A durable queue is **planned (N4)**.
- Isolation: runs share the host. Running each job in a container or sandbox is listed as future work in ADR-001 **(planned, L2)** and should ship before hosting runs for third parties.
- Dependencies: the App adds no runtime npm dependencies.

## 9. Success metrics (definitions only; there is no baseline yet)

- Activation: share of installations with at least one successful draft PR within 7 days of installing.
- Run success rate: draft PRs opened ÷ labelled runs with a valid spec.
- Review acceptance: draft PRs merged ÷ opened.
- Time to PR: from label to PR opened (p50/p95).

No targets are set until there is real usage.

## 10. Pricing and positioning (assumptions for the owner)

- **Licensing constraint:** the repository is MIT (`LICENSE`), so anyone can self-host the CLI and this App for free. Revenue can come only from (a) a **hosted** App (convenience, isolation, support) and (b) recipe packs that are **not** in this MIT repo. The owner must decide where paid recipes live and under which license (Q1).
- Positioning: "Reviewed scaffolding: every generated change arrives as a draft PR." This rests on ADR-001/003, not on AI generation, which the code does not do for Forge today.
- Possible packaging **(assumption, not validated)**: a free tier for public repos or N runs per month, a paid hosted tier per org, and recipe packs as a one-off or annual licence. No prices are proposed until Q2 and Q3 are answered.

## 11. Risks

| Risk | Mitigation |
|---|---|
| Hosted runs execute recipe templates for many tenants on shared hosts | Per-job sandbox (L2) before any hosted offering. Recipes remain allowlisted. |
| Anyone who can open an issue can author a spec | Only users who can label (triage+) can trigger a run. The spec is schema-validated, and output is a draft PR that needs review. |
| The PM-OS backend is mistaken for part of the product | It is excluded here. P0 authorization work must finish before any hosted offering (ROADMAP). |
| MIT licence limits monetisation of the CLI itself | Sell hosting and separate recipe packs (Q1). |
| Only two recipes today | Recipe packs are the growth lever. The pack format needs an ADR (L1). |

## 12. Open questions for the owner

1. Q1: Where do paid recipe packs live (private repo or registry), and under which licence?
2. Q2: Hosted, self-hosted, or both for the App's first release?
3. Q3: Who is the first design-partner segment (section 2)?
4. Q4: Where does generated output go in the target repo: the repo root (new, empty repos only), a subdirectory named after `projectName`, or a new repo? This blocks N2.
5. Q5: May the App comment on issues (needs `issues: write`) to report failures (US4)?
6. Q6: Should the trigger label be restricted further, for example to a list of allowed users or teams?
