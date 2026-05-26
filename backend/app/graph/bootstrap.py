from typing import Any

from core.config import settings

SCHEMA_VERSION = 2

MIGRATIONS: dict[int, list[str]] = {
    1: [
        "CREATE CONSTRAINT projectforge_node_id IF NOT EXISTS FOR (n) REQUIRE n.id IS UNIQUE",
    ],
    2: [
        "CREATE INDEX projectforge_project_id IF NOT EXISTS FOR (n) ON (n.project_id)",
        "CREATE INDEX projectforge_node_label IF NOT EXISTS FOR (n) ON (n.label)",
    ],
}


def bootstrap_neo4j(driver, database: str | None = None) -> dict[str, Any]:
    applied: list[str] = []
    warnings: list[str] = []
    current_version = 0
    session_kwargs: dict[str, Any] = {}
    if database:
        session_kwargs["database"] = database

    with driver.session(**session_kwargs) as session:
        record = session.run(
            "MERGE (meta:ProjectForgeMeta {id: 'schema'}) "
            "ON CREATE SET meta.version = 0 "
            "RETURN meta.version AS version"
        ).single()
        if record:
            current_version = int(record["version"] or 0)

        for version in range(current_version + 1, SCHEMA_VERSION + 1):
            for statement in MIGRATIONS.get(version, []):
                try:
                    session.run(statement)
                    applied.append(statement)
                except Exception as exc:
                    warnings.append(f"v{version} {statement}: {exc}")
            session.run(
                "MERGE (meta:ProjectForgeMeta {id: 'schema'}) SET meta.version = $version",
                version=version,
            )
            current_version = version

    return {
        "status": "bootstrapped",
        "uri": settings.NEO4J_URI,
        "database": database,
        "schema_version": current_version,
        "target_version": SCHEMA_VERSION,
        "applied": len(applied),
        "warnings": warnings,
    }
