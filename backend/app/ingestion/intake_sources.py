from typing import Any

from ingestion.parsers.base import ParsedChunk, ParsedDocument, normalize_text
from ingestion.parsers.common.cad_bim import parse_dwg, parse_ifc
from ingestion.parsers.common.codebase import parse_code_archive


def snapshot_postgres_schema(
    connection_uri: str,
    *,
    schema: str = "public",
    source_label: str = "postgres_schema",
) -> ParsedDocument:
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError("psycopg is required for database schema snapshots") from exc

    warnings: list[str] = []
    lines = [f"PostgreSQL schema snapshot: {schema}"]

    with psycopg.connect(connection_uri, connect_timeout=5) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = %s AND table_type = 'BASE TABLE'
                ORDER BY table_name
                """,
                (schema,),
            )
            tables = [row[0] for row in cur.fetchall()]
            lines.append(f"Tables: {len(tables)}")

            for table in tables:
                cur.execute(
                    """
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s
                    ORDER BY ordinal_position
                    """,
                    (schema, table),
                )
                columns = cur.fetchall()
                lines.append(f"\nTable {table} ({len(columns)} columns)")
                for column_name, data_type, is_nullable in columns:
                    null_flag = "NULL" if is_nullable == "YES" else "NOT NULL"
                    lines.append(f"- {column_name}: {data_type} {null_flag}")

            cur.execute(
                """
                SELECT tc.table_name, kcu.column_name, ccu.table_name, ccu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                 AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage ccu
                  ON ccu.constraint_name = tc.constraint_name
                 AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = %s
                ORDER BY tc.table_name, kcu.column_name
                """,
                (schema,),
            )
            foreign_keys = cur.fetchall()
            if foreign_keys:
                lines.append(f"\nForeign keys: {len(foreign_keys)}")
                for table_name, column_name, ref_table, ref_column in foreign_keys:
                    lines.append(
                        f"- {table_name}.{column_name} -> {ref_table}.{ref_column}"
                    )

    summary = normalize_text("\n".join(lines))
    chunks = [
        ParsedChunk(
            source=source_label,
            text=summary,
            metadata={
                "parser": "database_schema",
                "source": source_label,
                "db_engine": "postgresql",
                "schema": schema,
                "table_count": len(tables),
                "chunk_index": 1,
            },
        )
    ]

    return ParsedDocument(
        source=source_label,
        chunks=chunks,
        metadata={
            "parser": "database_schema",
            "source": source_label,
            "db_engine": "postgresql",
            "schema": schema,
            "chunk_count": len(chunks),
            "table_count": len(tables),
        },
        warnings=warnings,
    )


def parse_cad_bim(source: Any, *, filename: str):
    lower = filename.lower()
    if lower.endswith(".ifc"):
        return parse_ifc(source, filename=filename)
    if lower.endswith(".dwg"):
        return parse_dwg(source, filename=filename)
    raise ValueError(f"Unsupported CAD/BIM file: {filename}")


def parse_folder_archive(source: Any, *, filename: str):
    lower = filename.lower()
    if lower.endswith((".zip", ".tar", ".tar.gz", ".tgz")):
        return parse_code_archive(source, filename=filename)
    raise ValueError(f"Unsupported codebase archive: {filename}")
