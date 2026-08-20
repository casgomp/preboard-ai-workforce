-- Document inventory, ownership and audience controls.
SELECT document_id, title, filename, department, owner_name, owner_email,
  audience, status, created_at, chunk_count
FROM company_documents
ORDER BY created_at DESC;

-- Candidate-safe retrieval corpus. HR queries may omit the audience predicate.
SELECT c.chunk_id, c.document_id, d.title, d.department, d.owner_name,
  d.owner_email, d.audience, c.content
FROM document_chunks c
JOIN company_documents d USING (document_id)
WHERE d.status = 'READY'
  AND d.audience = 'ALL_EMPLOYEES';

-- Databricks Vector Search can index document_chunks after an embedding column
-- or managed embedding index is configured. Retrieval must return document_id
-- so every generated answer can cite its supporting source.
