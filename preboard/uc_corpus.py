"""Corpus storage in Unity Catalog (NOTES.md §2/§9): a Delta table replacing the local
markdown files `LocalMarkdownSource` reads. Import of the SDK is deferred, same
reasoning as generation.py/embedding_retrieval.py: the rest of the app runs without
`databricks-sdk` installed or credentials configured.

Embeddings are still computed live per question (embedding_retrieval.py) rather than
stored here — this table holds the raw chunk text UC is meant to hold, not a vector
index. See NOTES.md §2 for why a managed Vector Search index isn't used at this scale.
"""
from __future__ import annotations

from pathlib import Path

from preboard.corpus import Chunk, load_chunks

CATALOG = "workspace"
SCHEMA = "preboard"
TABLE = "offer_chunks"
FULL_TABLE_NAME = f"{CATALOG}.{SCHEMA}.{TABLE}"


class UnityCatalogSource:
    """Reads chunks for one offer from `workspace.preboard.offer_chunks`."""

    def __init__(self, warehouse_id: str):
        from databricks.sdk import WorkspaceClient  # noqa: PLC0415

        self._warehouse_id = warehouse_id
        self._client = WorkspaceClient()

    def load(self, offer_id: str) -> list[Chunk]:
        from databricks.sdk.service.sql import StatementParameterListItem  # noqa: PLC0415

        response = self._client.statement_execution.execute_statement(
            statement=(
                f"SELECT doc_id, section, text FROM {FULL_TABLE_NAME} "
                "WHERE offer_id = :offer_id ORDER BY chunk_order"
            ),
            warehouse_id=self._warehouse_id,
            parameters=[StatementParameterListItem(name="offer_id", value=offer_id, type="STRING")],
            wait_timeout="30s",
        )
        rows = response.result.data_array if response.result else None
        if not rows:
            return []
        return [Chunk(doc_id=row[0], section=row[1], text=row[2]) for row in rows]


def ensure_schema_and_table(client, warehouse_id: str) -> None:
    for statement in (
        f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}",
        f"""
        CREATE TABLE IF NOT EXISTS {FULL_TABLE_NAME} (
            offer_id STRING,
            doc_id STRING,
            section STRING,
            text STRING,
            chunk_order INT
        )
        """,
    ):
        response = client.statement_execution.execute_statement(
            statement=statement, warehouse_id=warehouse_id, wait_timeout="30s"
        )
        if response.status.state.value == "FAILED":
            raise RuntimeError(f"schema/table setup failed: {response.status.error}")


def ingest(corpus_dir: Path, warehouse_id: str) -> int:
    """Replaces the table contents with every `<corpus_dir>/*.md` file's chunks.
    Idempotent — safe to re-run after editing a local offer packet.

    Parameterized inserts, not string-interpolated SQL: a first version built one
    giant VALUES literal by hand-escaping quotes with SQL's standard `''` doubling,
    which Spark SQL silently ignores (it expects `\\'`, not `''`) — "hasn't" round-
    tripped as "hasnt" with no error. Parameters sidestep escaping entirely.
    """
    from databricks.sdk import WorkspaceClient  # noqa: PLC0415
    from databricks.sdk.service.sql import StatementParameterListItem  # noqa: PLC0415

    client = WorkspaceClient()
    ensure_schema_and_table(client, warehouse_id)

    def run(statement: str, parameters: list[StatementParameterListItem] | None = None):
        response = client.statement_execution.execute_statement(
            statement=statement, warehouse_id=warehouse_id, parameters=parameters, wait_timeout="30s"
        )
        if response.status.state.value == "FAILED":
            raise RuntimeError(f"ingest failed: {response.status.error}")
        return response

    run(f"DELETE FROM {FULL_TABLE_NAME}")

    count = 0
    for doc_path in sorted(corpus_dir.glob("*.md")):
        offer_id = doc_path.stem
        for i, chunk in enumerate(load_chunks(doc_path)):
            run(
                f"INSERT INTO {FULL_TABLE_NAME} (offer_id, doc_id, section, text, chunk_order) "
                "VALUES (:offer_id, :doc_id, :section, :text, :chunk_order)",
                parameters=[
                    StatementParameterListItem(name="offer_id", value=offer_id, type="STRING"),
                    StatementParameterListItem(name="doc_id", value=chunk.doc_id, type="STRING"),
                    StatementParameterListItem(name="section", value=chunk.section, type="STRING"),
                    StatementParameterListItem(name="text", value=chunk.text, type="STRING"),
                    StatementParameterListItem(name="chunk_order", value=str(i), type="INT"),
                ],
            )
            count += 1

    return count


def main() -> None:
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Ingest data/*.md into Unity Catalog")
    parser.add_argument(
        "--corpus-dir", type=Path, default=Path(__file__).resolve().parent.parent / "data"
    )
    parser.add_argument("--warehouse-id", default=os.environ.get("DATABRICKS_WAREHOUSE_ID"))
    args = parser.parse_args()

    if not args.warehouse_id:
        raise SystemExit("--warehouse-id or DATABRICKS_WAREHOUSE_ID is required")

    count = ingest(args.corpus_dir, args.warehouse_id)
    print(f"Ingested {count} chunks into {FULL_TABLE_NAME}")


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    main()
