# ProjectForgeAi — Vision & v1 Scope

## Problem

Turning a product or technical spec into a working repository is repetitive: folder layout, CI, README, starter tests, and boilerplate configs. Teams redo this for every greenfield project. AI assistants help ad hoc, but output is inconsistent, hard to audit, and risky to apply without guardrails.

## Vision

**ProjectForgeAi** is a spec-driven project generator that produces reproducible, reviewable repository scaffolding from versioned **forge recipes**—not one-off chat output.

Success looks like:

1. A human or system provides a structured spec (or selects a recipe).
2. The forge runs in a controlled, auditable way.
3. Output lands as a **pull request** (or local directory) with CI-ready structure.
4. The same inputs + recipe version yield the same file tree (within defined variance).

## Target users (v1)

- **Solo developers** bootstrapping small services or apps.
- **Platform / DevEx teams** maintaining internal starter templates.

Enterprise multi-tenant SaaS is out of scope for v1 but informed by ADRs.

## v1 scope (in)

- CLI: `forge run --recipe <name> --output <dir>`
- One built-in recipe: **minimal** (README, package.json stub, CI workflow)
- Recipe versioning via directory layout under `templates/`
- Local output directory only (no auto GitHub PR creation yet)
- Documentation: vision, architecture, execution model ADR
- CI: build, test, smoke-run minimal forge in temp dir

## v1 scope (out)

- LLM-based spec interpretation (planned; hooks reserved)
- Hosted web UI or API
- Auto-commit to remote repositories
- Notion / Linear / Jira integrations
- Custom recipe marketplace
- Multi-language recipes beyond Node/TypeScript template

## Non-goals

- Replacing full application development or domain logic generation at scale without review.
- Running arbitrary shell from user specs without sandboxing (see ADR-001).
- Storing customer specs in a central cloud by default.

## Principles

1. **Reproducibility** — Recipes are versioned; forge runs are logged.
2. **Review before merge** — Default path is PR or manual copy, not force-push.
3. **Least privilege** — No secrets in generated output; placeholders only.
4. **Test the forge** — Golden-path tests for each recipe in CI.

## Success metrics (v1)

- `minimal` recipe runs in CI without network (except npm install for build).
- New contributor can run forge locally in under 5 minutes after clone.
- ADR-001 execution constraints documented and reflected in CLI behavior.
