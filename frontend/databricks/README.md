# Databricks setup

This folder is the explainable Databricks path for Day One Digital Twin. Mock mode is the default and needs no external service.

1. Select a catalog and schema in Databricks SQL.
2. Run `setup_tables.sql`.
3. Run `seed_data.sql` for fictional demo records, then `seed_fact_events.sql` once
   for the candidate dashboard's "recent changes" feed (PLAN_PR15 B5) — kept
   separate from `seed_data.sql` for the same `INSERT OVERWRITE`-wipes-everything
   reason `question_misses` is.
4. Use `fact_layer_query.sql`, `readiness_query.sql`, and `blockers_query.sql` to explain the shared intelligence layer.
5. Set the server-only environment variables documented in the project README, then choose `DATA_MODE=databricks`.

For company-document storage, also run the document tables in `setup_tables.sql`, set `DOCUMENT_MODE=databricks`, and use `documents_query.sql` as the retrieval contract. Raw file bytes remain in object storage while extracted text, chunks, ownership and audience controls live in Delta tables. This separation keeps original documents durable and makes grounded retrieval explainable.

The TypeScript provider uses the Databricks SQL Statement Execution API. Its deliberate mapping placeholder must be adapted to the column metadata returned by the target workspace before production use; the app surfaces that limitation instead of pretending a connection is working.

## The Python brain (PR12/NOTES.md §19)

The chat at `/candidate` is answered by `preboard/` (FastAPI `server.py`), not TypeScript — it reads `document_chunks`/`company_documents` for grounded answers and `department_contacts` for routing a handoff, and writes to `question_misses` when it can't answer confidently.

- Ingest the offer-packet corpus: `python -m preboard.uc_corpus --warehouse-id <id>` (reads `DATABRICKS_CATALOG`/`DATABRICKS_SCHEMA` from the environment, defaulting to `workspace`/`preboard`). Safe to re-run after editing a local packet in `data/*.md` — it deletes and reinserts `document_chunks`/`company_documents` only.
- **Never re-run `seed_data.sql` after a demo has started.** Its `INSERT OVERWRITE` statements wipe every table they touch, `question_misses` included if it were ever added there — that's exactly why `question_misses` is created in `setup_tables.sql` and populated live by the app instead, not seeded.
