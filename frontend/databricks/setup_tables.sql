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

CREATE TABLE IF NOT EXISTS document_chunks (
  chunk_id STRING, document_id STRING, chunk_index INT, content STRING
) USING DELTA;

CREATE TABLE IF NOT EXISTS department_contacts (
  department STRING, person_name STRING, email STRING, routing_terms ARRAY<STRING>
) USING DELTA;
