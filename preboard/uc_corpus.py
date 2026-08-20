"""Corpus storage in Unity Catalog (PR12/NOTES.md §19): `document_chunks` joined to
`company_documents` — the frontend's schema (`frontend/databricks/setup_tables.sql`),
not the old `workspace.preboard.offer_chunks` from PR3. Two parallel schemas meant the
HR dashboard and the chat answered from different tables; this converges on one.

Rewritten against the new tables, not deleted: the parameterized-insert pattern below
is what any future ingestion path needs, same lesson as PR3 (NOTES.md §11 — Spark
SQL's `''` quote-doubling silently drops characters; parameters sidestep it
entirely).

Embeddings are still computed live per question (embedding_retrieval.py) rather than
stored here — see NOTES.md §2.
"""
from __future__ import annotations

import os
from pathlib import Path

from preboard.corpus import SHARED_DOC_ID, Chunk, load_chunks

DEFAULT_CATALOG = "workspace"
DEFAULT_SCHEMA = "preboard"

# Friendly citation titles (Answer.citations[].title, matching the frontend's
# GroundedAnswer contract) — company_documents.title, not the bare document_id.
_DOCUMENT_TITLES = {
    "E001": "Anna Müller — Offer Packet",
    "E002": "David Klein — Offer Packet",
    SHARED_DOC_ID: "Employee Handbook",
}


def catalog_and_schema() -> tuple[str, str]:
    """PR12 D6: the frontend's env var names win — DATABRICKS_CATALOG/
    DATABRICKS_SCHEMA replace Python's old hardcoded 'workspace'/'preboard'
    constants, defaulted here only for backward-compatible local dev."""
    return (
        os.environ.get("DATABRICKS_CATALOG", DEFAULT_CATALOG),
        os.environ.get("DATABRICKS_SCHEMA", DEFAULT_SCHEMA),
    )


class UnityCatalogSource:
    """Reads chunks for one employee, plus the shared handbook (corpus.py's
    SHARED_DOC_ID), from `document_chunks` joined to `company_documents` for the
    citation title."""

    def __init__(self, warehouse_id: str):
        from databricks.sdk import WorkspaceClient  # noqa: PLC0415

        catalog, schema = catalog_and_schema()
        self._warehouse_id = warehouse_id
        self._chunks_table = f"{catalog}.{schema}.document_chunks"
        self._docs_table = f"{catalog}.{schema}.company_documents"
        self._client = WorkspaceClient()

    def load(self, offer_id: str) -> list[Chunk]:
        from databricks.sdk.service.sql import StatementParameterListItem  # noqa: PLC0415

        response = self._client.statement_execution.execute_statement(
            statement=(
                "SELECT dc.document_id, dc.section, dc.content, cd.title "
                f"FROM {self._chunks_table} dc LEFT JOIN {self._docs_table} cd "
                "ON dc.document_id = cd.document_id "
                "WHERE dc.document_id = :offer_id OR dc.document_id = :shared_id "
                # Employee chunks before the shared handbook, matching
                # LocalMarkdownSource's fixed order — see PR3/NOTES.md §14 for the
                # ordering bug this CASE avoids (plain ORDER BY document_id put the
                # handbook before or after employee chunks inconsistently depending
                # on alphabetical order).
                "ORDER BY CASE WHEN dc.document_id = :offer_id THEN 0 ELSE 1 END, dc.chunk_index"
            ),
            warehouse_id=self._warehouse_id,
            parameters=[
                StatementParameterListItem(name="offer_id", value=offer_id, type="STRING"),
                StatementParameterListItem(name="shared_id", value=SHARED_DOC_ID, type="STRING"),
            ],
            wait_timeout="30s",
        )
        rows = response.result.data_array if response.result else None
        if not rows:
            return []
        return [Chunk(doc_id=row[0], section=row[1], text=row[2], title=row[3]) for row in rows]


def ensure_schema_and_table(client, warehouse_id: str, catalog: str, schema: str) -> None:
    for statement in (
        f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}",
        f"""
        CREATE TABLE IF NOT EXISTS {catalog}.{schema}.company_documents (
            document_id STRING, title STRING, filename STRING, mime_type STRING,
            department STRING, owner_name STRING, owner_email STRING, audience STRING,
            raw_storage_uri STRING, extracted_text STRING, status STRING, uploaded_by STRING,
            created_at TIMESTAMP, chunk_count INT
        )
        """,
        # `section` is this ingestion path's own addition to the frontend's
        # document_chunks — needed for citations to name a section, not just a
        # document (NOTES.md §19).
        f"""
        CREATE TABLE IF NOT EXISTS {catalog}.{schema}.document_chunks (
            chunk_id STRING, document_id STRING, chunk_index INT, section STRING, content STRING
        )
        """,
    ):
        response = client.statement_execution.execute_statement(
            statement=statement, warehouse_id=warehouse_id, wait_timeout="30s"
        )
        if response.status.state.value == "FAILED":
            raise RuntimeError(f"schema/table setup failed: {response.status.error}")


def ingest(corpus_dir: Path, warehouse_id: str) -> int:
    """Replaces document_chunks/company_documents contents with every
    `<corpus_dir>/*.md` file's chunks. Idempotent — safe to re-run after editing a
    local packet. Does not touch department_contacts, employees, or question_misses —
    those are `frontend/databricks/seed_data.sql`'s and the running app's, not this
    ingestion path's, concern."""
    from databricks.sdk import WorkspaceClient  # noqa: PLC0415
    from databricks.sdk.service.sql import StatementParameterListItem  # noqa: PLC0415

    catalog, schema = catalog_and_schema()
    chunks_table = f"{catalog}.{schema}.document_chunks"
    docs_table = f"{catalog}.{schema}.company_documents"

    client = WorkspaceClient()
    ensure_schema_and_table(client, warehouse_id, catalog, schema)

    def run(statement: str, parameters: list[StatementParameterListItem] | None = None):
        response = client.statement_execution.execute_statement(
            statement=statement, warehouse_id=warehouse_id, parameters=parameters, wait_timeout="30s"
        )
        if response.status.state.value == "FAILED":
            raise RuntimeError(f"ingest failed: {response.status.error}")
        return response

    run(f"DELETE FROM {chunks_table}")
    run(f"DELETE FROM {docs_table}")

    count = 0
    for doc_path in sorted(corpus_dir.glob("*.md")):
        document_id = doc_path.stem
        chunks = load_chunks(doc_path)

        run(
            f"INSERT INTO {docs_table} "
            "(document_id, title, department, audience, status, created_at, chunk_count) "
            "VALUES (:document_id, :title, :department, :audience, :status, "
            "current_timestamp(), :chunk_count)",
            parameters=[
                StatementParameterListItem(name="document_id", value=document_id, type="STRING"),
                StatementParameterListItem(
                    name="title", value=_DOCUMENT_TITLES.get(document_id, document_id), type="STRING"
                ),
                StatementParameterListItem(name="department", value="Preboarding", type="STRING"),
                StatementParameterListItem(name="audience", value="ALL_EMPLOYEES", type="STRING"),
                StatementParameterListItem(name="status", value="READY", type="STRING"),
                StatementParameterListItem(name="chunk_count", value=str(len(chunks)), type="INT"),
            ],
        )

        for i, chunk in enumerate(chunks):
            run(
                f"INSERT INTO {chunks_table} (chunk_id, document_id, chunk_index, section, content) "
                "VALUES (:chunk_id, :document_id, :chunk_index, :section, :content)",
                parameters=[
                    StatementParameterListItem(
                        name="chunk_id", value=f"{document_id}-{i}", type="STRING"
                    ),
                    StatementParameterListItem(name="document_id", value=document_id, type="STRING"),
                    StatementParameterListItem(name="chunk_index", value=str(i), type="INT"),
                    StatementParameterListItem(name="section", value=chunk.section, type="STRING"),
                    StatementParameterListItem(name="content", value=chunk.text, type="STRING"),
                ],
            )
            count += 1

    return count


def main() -> None:
    import argparse

    from preboard.wiring import resolve_warehouse_id

    parser = argparse.ArgumentParser(description="Ingest data/*.md into Unity Catalog")
    parser.add_argument(
        "--corpus-dir", type=Path, default=Path(__file__).resolve().parent.parent / "data"
    )
    parser.add_argument("--warehouse-id", default=resolve_warehouse_id())
    args = parser.parse_args()

    if not args.warehouse_id:
        raise SystemExit("--warehouse-id, DATABRICKS_WAREHOUSE_ID, or DATABRICKS_HTTP_PATH is required")

    count = ingest(args.corpus_dir, args.warehouse_id)
    catalog, schema = catalog_and_schema()
    print(f"Ingested {count} chunks into {catalog}.{schema}.document_chunks")


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    main()
