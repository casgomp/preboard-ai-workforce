# Databricks setup

This folder is the explainable Databricks path for Day One Digital Twin. Mock mode is the default and needs no external service.

1. Select a catalog and schema in Databricks SQL.
2. Run `setup_tables.sql`.
3. Run `seed_data.sql` for fictional demo records.
4. Use `fact_layer_query.sql`, `readiness_query.sql`, and `blockers_query.sql` to explain the shared intelligence layer.
5. Set the server-only environment variables documented in the project README, then choose `DATA_MODE=databricks`.

For company-document storage, also run the document tables in `setup_tables.sql`, set `DOCUMENT_MODE=databricks`, and use `documents_query.sql` as the retrieval contract. Raw file bytes remain in object storage while extracted text, chunks, ownership and audience controls live in Delta tables. This separation keeps original documents durable and makes grounded retrieval explainable.

The TypeScript provider uses the Databricks SQL Statement Execution API. Its deliberate mapping placeholder must be adapted to the column metadata returned by the target workspace before production use; the app surfaces that limitation instead of pretending a connection is working.
