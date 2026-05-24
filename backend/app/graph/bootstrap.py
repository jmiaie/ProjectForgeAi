from typing import Any

from core.config import settings

CONSTRAINTS = [
    "CREATE CONSTRAINT projectforge_node_id IF NOT EXISTS FOR (n) REQUIRE n.id IS UNIQUE",
]

INDEXES = [
    "CREATE INDEX projectforge_project_id IF NOT EXISTS FOR (n) ON (n.project_id)",
    "CREATE INDEX projectforge_node_label IF NOT EXISTS FOR (n) ON (n.label)",
]


def bootstrap_neo4j(driver) -> dict[str, Any]:
    applied: list[str] = []
    warnings: list[str] = []
    with driver.session() as session:
        for statement in CONSTRAINTS + INDEXES:
            try:
                session.run(statement)
                applied.append(statement)
            except Exception as exc:
                warnings.append(f"{statement}: {exc}")
    return {
        "status": "bootstrapped",
        "uri": settings.NEO4J_URI,
        "applied": len(applied),
        "warnings": warnings,
    }
