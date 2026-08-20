-- Day One Digital Twin — Databricks Delta schema
CREATE TABLE IF NOT EXISTS employees (
  employee_id STRING, name STRING, role STRING, department STRING, location STRING,
  manager_name STRING, start_date DATE, email STRING
) USING DELTA;

CREATE TABLE IF NOT EXISTS day_one_facts (
  fact_id STRING, employee_id STRING, fact_key STRING, fact_value STRING, category STRING,
  source_system STRING, owner_team STRING, last_updated TIMESTAMP, visibility STRING,
  verification_status STRING, previous_value STRING, internal_details STRING, candidate_safe_label STRING
) USING DELTA;

CREATE TABLE IF NOT EXISTS fact_events (
  event_id STRING, employee_id STRING, fact_key STRING, previous_value STRING,
  new_value STRING, source_system STRING, event_timestamp TIMESTAMP
) USING DELTA;

CREATE TABLE IF NOT EXISTS day_one_requirements (
  requirement_id STRING, fact_key STRING, requirement_name STRING, category STRING,
  weight DOUBLE, critical_for_day_one BOOLEAN
) USING DELTA;

CREATE TABLE IF NOT EXISTS company_knowledge (
  document_id STRING, title STRING, category STRING, location STRING, content STRING
) USING DELTA;

CREATE TABLE IF NOT EXISTS company_documents (
  document_id STRING, title STRING, filename STRING, mime_type STRING,
  department STRING, owner_name STRING, owner_email STRING, audience STRING,
  raw_storage_uri STRING, extracted_text STRING, status STRING, uploaded_by STRING,
  created_at TIMESTAMP, chunk_count INT
) USING DELTA;

-- section (PR12/NOTES.md §19): document_chunks originally had no way to name a
-- chunk beyond its index, so a Q&A citation could only ever point at a whole
-- document, not a section within it. preboard/uc_corpus.py writes one per chunk.
CREATE TABLE IF NOT EXISTS document_chunks (
  chunk_id STRING, document_id STRING, chunk_index INT, section STRING, content STRING
) USING DELTA;

-- covers (PR12/NOTES.md §19): routing_terms is the keyword-match path;
-- covers is the natural-language prose embedded for the semantic-match path
-- (preboard/routing.py's UnityCatalogDirectorySource) and what a handoff message
-- can quote back to the candidate. One row carries both.
CREATE TABLE IF NOT EXISTS department_contacts (
  department STRING, person_name STRING, email STRING, routing_terms ARRAY<STRING>,
  covers STRING
) USING DELTA;

-- question_misses (PR12/NOTES.md §19): the Python brain's miss log, converged into
-- this schema alongside document_chunks/department_contacts so the HR dashboard and
-- the chat read from one place. Seeded separately from seed_data.sql's INSERT
-- OVERWRITE pattern (frontend/databricks/README.md) — that pattern wipes a table on
-- every re-run, which would destroy the live-demo misses this table exists to keep.
-- days_to_start (PLAN_PR14 B5): nullable — populated from the real clock, never
-- from a demo `as_of` override (D5); NULL for rows logged before this column
-- existed or where QA.ask had no start_date. On an already-provisioned workspace
-- this CREATE TABLE IF NOT EXISTS won't retroactively add the column — run
-- `ALTER TABLE question_misses ADD COLUMN days_to_start INT` by hand once.
CREATE TABLE IF NOT EXISTS question_misses (
  miss_id STRING, employee_id STRING, question STRING,
  top_score DOUBLE, department STRING, days_to_start INT, logged_at TIMESTAMP
) USING DELTA;
