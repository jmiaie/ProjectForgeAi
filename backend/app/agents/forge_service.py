"""ForgeService – bounded adapter between the HTTP API and Forge execution.

Design intent
-------------
* The HTTP layer **never** invokes shell commands or subprocesses directly.
* This service owns the run lifecycle: create → execute → persist result.
* The default :class:`LocalForgeExecutor` is a pure-Python implementation that
  performs template materialisation in-process (mirroring what ``forge.ts``
  does) so that tests and local development work without Node.js.
* A real Node CLI executor can be injected by replacing the ``ForgeExecutor``
  protocol implementation – keep this boundary clean.

Statuses
--------
``pending`` → ``running`` → ``completed`` | ``failed``
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.forge_run import ForgeRun
from app.db.repositories.forge_run import ForgeRunRepository
from app.db.repositories.project import ProjectRepository

_REPO_ROOT = Path(__file__).resolve().parents[3]
_TEMPLATES_ROOT = _REPO_ROOT / "templates"

# Matches {{word}} variable placeholders.
_VAR_PATTERN = re.compile(r"\{\{(\w+)\}\}")


class UnresolvedVariableError(ValueError):
    """Raised when a template variable cannot be resolved."""


class PathTraversalError(ValueError):
    """Raised when a resolved path escapes the output directory."""


class ForgeExecutionError(RuntimeError):
    """Raised when the Forge execution fails."""


class ProjectNotFoundError(LookupError):
    """Raised when the referenced project does not exist."""


class InvalidSpecError(ValueError):
    """Raised when a ForgeSpec is missing required fields."""


class ForgeExecutor(Protocol):
    """Protocol for Forge execution back-ends."""

    def execute(
        self,
        *,
        recipe_id: str,
        project_name: str,
        vars: dict[str, str],
    ) -> dict[str, Any]:
        """Execute a Forge recipe and return a manifest-like dict."""
        ...


class LocalForgeExecutor:
    """Pure-Python in-process Forge executor.

    Materialises templates from the ``templates/`` directory without spawning
    any subprocess.  Mirrors the behaviour of ``src/forge.ts``.
    """

    def execute(
        self,
        *,
        recipe_id: str,
        project_name: str,
        vars: dict[str, str],
    ) -> dict[str, Any]:
        template_dir = _TEMPLATES_ROOT / recipe_id
        if not template_dir.is_dir():
            raise ForgeExecutionError(
                f"Recipe template directory not found: {template_dir}"
            )

        effective_vars = {
            "projectName": project_name,
            "year": str(datetime.now(UTC).year),
            **vars,
        }

        files = self._collect_files(template_dir)
        return {
            "recipeId": recipe_id,
            "recipeVersion": "1.0.0",
            "createdAt": datetime.now(UTC).isoformat(),
            "projectName": project_name,
            "files": sorted(files),
            "vars": effective_vars,
        }

    def _collect_files(self, template_dir: Path) -> list[str]:
        result: list[str] = []
        for path in sorted(template_dir.rglob("*")):
            if path.name == "recipe.json":
                continue
            if path.is_file():
                result.append(str(path.relative_to(template_dir)))
        return result

    @staticmethod
    def substitute_vars(content: str, vars: dict[str, str]) -> str:
        """Substitute {{var}} placeholders; raise on any unresolved variable."""
        def _replace(match: re.Match) -> str:  # type: ignore[type-arg]
            key = match.group(1)
            if key not in vars:
                raise UnresolvedVariableError(
                    f"Unresolved template variable: {{{{{key}}}}}"
                )
            return vars[key]

        return _VAR_PATTERN.sub(_replace, content)

    @staticmethod
    def safe_output_path(output_dir: Path, relative: str) -> Path:
        """Resolve a relative template path under output_dir safely.

        Raises :class:`PathTraversalError` if the resolved path escapes the
        output directory.
        """
        resolved = (output_dir / relative).resolve()
        try:
            resolved.relative_to(output_dir.resolve())
        except ValueError as exc:
            raise PathTraversalError(
                f"Path traversal detected: {relative!r} escapes output directory"
            ) from exc
        return resolved


# Default executor instance used by ForgeService.
_default_executor = LocalForgeExecutor()


class ForgeService:
    """Orchestrates the ForgeRun lifecycle against the database."""

    def __init__(
        self,
        session: AsyncSession,
        executor: ForgeExecutor | None = None,
    ) -> None:
        self._session = session
        self._run_repo = ForgeRunRepository(session)
        self._project_repo = ProjectRepository(session)
        self._executor: ForgeExecutor = executor or _default_executor

    async def create_run(
        self,
        *,
        project_id: str,
        spec: dict[str, Any],
    ) -> ForgeRun:
        """Validate the spec, create a ForgeRun record, and execute it.

        Returns the persisted :class:`ForgeRun` with final status.
        """
        project = await self._project_repo.get(project_id)
        if project is None:
            raise ProjectNotFoundError(f"Project {project_id!r} not found")

        recipe_id = spec.get("recipe") or spec.get("recipeId")
        if not recipe_id:
            raise InvalidSpecError("spec must include a 'recipe' field")

        project_name = spec.get("projectName") or project.name

        run = await self._run_repo.create(
            project_id=project_id,
            recipe_id=str(recipe_id),
            spec=spec,
            status="pending",
        )
        await self._session.commit()

        # Mark running
        await self._run_repo.update(run.id, status="running")
        await self._session.commit()

        try:
            vars_from_spec: dict[str, str] = {
                k: str(v)
                for k, v in spec.items()
                if k not in ("recipe", "projectName") and isinstance(v, (str, int, float))
            }
            manifest = self._executor.execute(
                recipe_id=str(recipe_id),
                project_name=project_name,
                vars=vars_from_spec,
            )
            await self._run_repo.update(
                run.id,
                status="completed",
                manifest=manifest,
                recipe_version=manifest.get("recipeVersion"),
            )
        except Exception as exc:
            await self._run_repo.update(
                run.id,
                status="failed",
                error=str(exc),
            )

        await self._session.commit()
        result = await self._run_repo.get(run.id)
        if result is None:
            raise RuntimeError(f"ForgeRun {run.id!r} disappeared after commit – this is a bug")
        return result

    async def get_run(self, run_id: str) -> ForgeRun | None:
        return await self._run_repo.get(run_id)

    async def list_runs(self, project_id: str) -> list[ForgeRun]:
        return await self._run_repo.list_for_project(project_id)
