# ADR-001: Execution Model

## Status

Accepted (2026-05-21)

## Context

ProjectForgeAi will eventually run AI-assisted and scripted steps that modify repositories. Uncontrolled execution risks secret leakage, supply-chain attacks, and unreviewed changes to `main`.

## Decision

### v1 execution rules

1. **Local directory output only** — `forge run` writes to a user-specified path; it does not `git push` or open PRs automatically.
2. **PR-only for upstream changes** — Any contribution to ProjectForgeAi itself goes through pull request; generated sample output is not committed to `main` (use `.gitignore` for `tmp-forge-output/`).
3. **Allowlisted recipes** — Only recipes registered in `src/recipes/` can run; arbitrary template paths are forbidden.
4. **No secrets in templates** — Generated files use placeholders (e.g. `YOUR_API_KEY`); validation will be added in a future ADR.
5. **Non-destructive by default** — Forge refuses to write into a non-empty directory unless `--force` is passed.
6. **Manifest per run** — Every run writes `forge.manifest.json` for audit and future incremental forges.

### Future (not v1)

- Sandboxed subprocess (container or `firejail`) for recipe hooks.
- GitHub App with least-privilege scopes for PR creation only.
- Explicit human approval step before apply.

## Consequences

- Users must manually `git init`, commit, and push forged projects.
- Safer defaults; slightly more friction until PR automation ships.
- CI smoke tests use isolated temp directories under the workspace.

## Alternatives considered

| Alternative | Why rejected for v1 |
|-------------|---------------------|
| Auto-push to `main` | Too risky for generated content |
| Clone arbitrary template URLs | Supply-chain and prompt-injection risk |
| Full shell access from specs | Requires sandbox not ready yet |
