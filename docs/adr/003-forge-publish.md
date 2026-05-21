# ADR-003: Forge Publish (Git + PR)

## Status

Accepted (2026-05-21)

## Context

ADR-001 requires review before merge. Operators need a scripted path from `forge run` output to a Git branch and pull request.

## Decision

1. **`forge publish --output <dir>`** prepares a git repository in the forged directory.
2. **Branch naming** — default `forge/<projectName>-<timestamp>`; overridable with `--branch`.
3. **Never push to `main`** — publish creates a feature branch only.
4. **`--push` + `--remote`** — pushes branch to `origin` when explicitly requested.
5. **GitHub CLI** — when `gh` is installed and authenticated, opens a **draft** PR via `gh pr create`.
6. **Manifest required** — publish refuses directories without `forge.manifest.json`.

## Consequences

- Safe default: local commit without network.
- CI does not require `gh` or GitHub tokens.
- Production automation can wrap `forge run` → `forge publish --push --remote …`.
