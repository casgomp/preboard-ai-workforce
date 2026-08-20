import { env } from "cloudflare:workers";
import { chunkDocument, extractDocumentText } from "./extract";
import type { CompanyDocument, DocumentAudience, SearchableChunk } from "./types";

type StatementResponse = { result?: { data_array?: unknown[][] }; status?: { state?: string; error?: { message?: string } } };

function config() {
  const host = process.env.DATABRICKS_HOST?.replace(/\/$/, "");
  const token = process.env.DATABRICKS_TOKEN;
  const warehouseId = process.env.DATABRICKS_HTTP_PATH?.split("/").at(-1);
  const catalog = process.env.DATABRICKS_CATALOG;
  const schema = process.env.DATABRICKS_SCHEMA;
  if (!host || !token || !warehouseId || !catalog || !schema) throw new Error("Databricks document mode is selected but its connection settings are incomplete.");
  return { host, token, warehouseId, catalog, schema };
}

function sql(value: string) { return `'${value.replaceAll("'", "''")}'`; }

async function statement(query: string) {
  const settings = config();
  const response = await fetch(`${settings.host}/api/2.0/sql/statements`, { method: "POST", headers: { Authorization: `Bearer ${settings.token}`, "Content-Type": "application/json" }, body: JSON.stringify({ warehouse_id: settings.warehouseId, catalog: settings.catalog, schema: settings.schema, statement: query, wait_timeout: "30s" }) });
  if (!response.ok) throw new Error(`Databricks document query failed with status ${response.status}.`);
  const payload = await response.json() as StatementResponse;
  if (payload.status?.state === "FAILED") throw new Error(payload.status.error?.message ?? "Databricks document query failed.");
  return payload.result?.data_array ?? [];
}

export async function listDatabricksDocuments(): Promise<CompanyDocument[]> {
  const rows = await statement("SELECT document_id,title,filename,mime_type,department,owner_name,owner_email,audience,status,created_at,chunk_count FROM company_documents ORDER BY created_at DESC");
  return rows.map((row) => ({ id: String(row[0]), title: String(row[1]), filename: String(row[2]), mimeType: String(row[3]), department: String(row[4]), ownerName: String(row[5]), ownerEmail: String(row[6]), audience: String(row[7]) as DocumentAudience, status: String(row[8]), createdAt: String(row[9]), chunkCount: Number(row[10]) }));
}

export async function databricksSearchableChunks(includeHR: boolean): Promise<SearchableChunk[]> {
  const rows = await statement(`SELECT c.chunk_id,c.document_id,d.title,d.department,d.owner_name,d.owner_email,d.audience,c.content FROM document_chunks c JOIN company_documents d USING (document_id) WHERE d.status='READY' ${includeHR ? "" : "AND d.audience='ALL_EMPLOYEES'"}`);
  return rows.map((row) => ({ id: String(row[0]), documentId: String(row[1]), title: String(row[2]), department: String(row[3]), ownerName: String(row[4]), ownerEmail: String(row[5]), audience: String(row[6]) as DocumentAudience, content: String(row[7]) }));
}

export async function saveDatabricksDocument(file: File, metadata: { title: string; department: string; ownerName: string; ownerEmail: string; audience: DocumentAudience; uploadedBy: string }): Promise<CompanyDocument> {
  if (!env.DOCS) throw new Error("Raw document storage is unavailable.");
  const extractedText = await extractDocumentText(file);
  const chunks = chunkDocument(extractedText);
  const id = crypto.randomUUID();
  const createdAt = new Date().toISOString();
  const storageKey = `company-documents/${id}/${file.name.replace(/[^a-zA-Z0-9._-]/g, "-")}`;
  await env.DOCS.put(storageKey, await file.arrayBuffer(), { httpMetadata: { contentType: file.type || "application/octet-stream" } });
  await statement(`INSERT INTO company_documents VALUES (${sql(id)},${sql(metadata.title)},${sql(file.name)},${sql(file.type || "application/octet-stream")},${sql(metadata.department)},${sql(metadata.ownerName)},${sql(metadata.ownerEmail)},${sql(metadata.audience)},${sql(storageKey)},${sql(extractedText)},'READY',${sql(metadata.uploadedBy)},CAST(${sql(createdAt)} AS TIMESTAMP),${chunks.length})`);
  if (chunks.length) await statement(`INSERT INTO document_chunks (chunk_id,document_id,chunk_index,content) VALUES ${chunks.map((content, index) => `(${sql(`${id}-${index}`)},${sql(id)},${index},${sql(content)})`).join(",")}`);
  return { id, title: metadata.title, filename: file.name, mimeType: file.type, department: metadata.department, ownerName: metadata.ownerName, ownerEmail: metadata.ownerEmail, audience: metadata.audience, status: "READY", createdAt, chunkCount: chunks.length };
}
