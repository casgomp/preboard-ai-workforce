import { getDocumentBindings } from "../../db";
import { chunkDocument, extractDocumentText } from "./extract";
import type { CompanyDocument, DocumentAudience, SearchableChunk } from "./types";

const seedDocuments = [
  { id: "DOC-WOB-ARRIVAL", title: "Wolfsburg First-Day Guide", filename: "wolfsburg-first-day.md", mimeType: "text/markdown", department: "People Operations", ownerName: "Julia Hartmann", ownerEmail: "people-operations@dayone.demo", audience: "ALL_EMPLOYEES" as const, text: "Your first day begins at 08:45 at the North Lobby of the Wolfsburg office. Bring a government-issued photo ID for reception. Smart casual clothing is appropriate; you do not need formal business attire. Your manager meets you at 09:00, followed by laptop setup at 09:30, team introductions at 10:30, lunch at 12:00 and orientation at 14:00. Visitor parking is beside the North Lobby, and reception can validate your visitor pass." },
  { id: "DOC-IT-SETUP", title: "Employee IT Setup Guide", filename: "employee-it-setup.md", mimeType: "text/markdown", department: "Workplace IT", ownerName: "Michael Braun", ownerEmail: "workplace-it@dayone.demo", audience: "ALL_EMPLOYEES" as const, text: "Workplace IT provides the assigned laptop during the 09:30 setup session. The employee account and multi-factor authentication are activated with an IT specialist. Required software is installed from the company software portal. Never share a password or authentication code. For device, account or software access problems, contact Workplace IT at workplace-it@dayone.demo." },
  { id: "DOC-HR-PAPERWORK", title: "New Starter Paperwork Guide", filename: "starter-paperwork.md", mimeType: "text/markdown", department: "People Operations", ownerName: "Julia Hartmann", ownerEmail: "people-operations@dayone.demo", audience: "ALL_EMPLOYEES" as const, text: "New starters must provide any requested tax identification and payroll documents through the secure employee portal before the stated deadline. Do not send identity documents by ordinary email. People Operations confirms when payroll information is complete. Questions about contracts, payroll documents or employee records should be sent to people-operations@dayone.demo." },
  { id: "DOC-HR-OPS", title: "HR Day One Escalation Playbook", filename: "hr-escalation-playbook.md", mimeType: "text/markdown", department: "People Operations", ownerName: "Sarah Weber", ownerEmail: "sarah.weber@dayone.demo", audience: "HR_ONLY" as const, text: "HR must escalate a delayed critical Day One fact when the employee starts within seven days. For a delayed laptop, the approved first response is to ask Workplace IT to reserve a temporary device. For a delayed badge, Facilities should prepare temporary building access. Every intervention must retain the source fact, accountable owner and event timestamp." },
];

let initialized = false;

async function ensureSchemaAndSeeds() {
  const { db } = getDocumentBindings();
  if (!initialized) {
    await db.batch([
      db.prepare("CREATE TABLE IF NOT EXISTS company_documents (id TEXT PRIMARY KEY NOT NULL, title TEXT NOT NULL, filename TEXT NOT NULL, mime_type TEXT NOT NULL, department TEXT NOT NULL, owner_name TEXT NOT NULL, owner_email TEXT NOT NULL, audience TEXT NOT NULL DEFAULT 'ALL_EMPLOYEES', storage_key TEXT NOT NULL, extracted_text TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'READY', uploaded_by TEXT NOT NULL, created_at TEXT NOT NULL)"),
      db.prepare("CREATE INDEX IF NOT EXISTS idx_company_documents_department ON company_documents(department)"),
      db.prepare("CREATE INDEX IF NOT EXISTS idx_company_documents_audience ON company_documents(audience)"),
      db.prepare("CREATE TABLE IF NOT EXISTS document_chunks (id TEXT PRIMARY KEY NOT NULL, document_id TEXT NOT NULL REFERENCES company_documents(id) ON DELETE CASCADE, chunk_index INTEGER NOT NULL, content TEXT NOT NULL)"),
      db.prepare("CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id ON document_chunks(document_id)"),
    ]);
    initialized = true;
  }
  const row = await db.prepare("SELECT COUNT(*) AS count FROM company_documents").first<{ count: number }>();
  if (Number(row?.count ?? 0) === 0) {
    const statements: D1PreparedStatement[] = [];
    for (const document of seedDocuments) {
      statements.push(db.prepare("INSERT INTO company_documents (id,title,filename,mime_type,department,owner_name,owner_email,audience,storage_key,extracted_text,status,uploaded_by,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)").bind(document.id, document.title, document.filename, document.mimeType, document.department, document.ownerName, document.ownerEmail, document.audience, `seed://${document.filename}`, document.text, "READY", "system-seed", new Date().toISOString()));
      chunkDocument(document.text).forEach((content, index) => statements.push(db.prepare("INSERT INTO document_chunks (id,document_id,chunk_index,content) VALUES (?,?,?,?)").bind(`${document.id}-${index}`, document.id, index, content)));
    }
    await db.batch(statements);
  }
  return getDocumentBindings();
}

export async function listDocuments(): Promise<CompanyDocument[]> {
  const { db } = await ensureSchemaAndSeeds();
  const result = await db.prepare("SELECT d.id,d.title,d.filename,d.mime_type AS mimeType,d.department,d.owner_name AS ownerName,d.owner_email AS ownerEmail,d.audience,d.status,d.created_at AS createdAt,COUNT(c.id) AS chunkCount FROM company_documents d LEFT JOIN document_chunks c ON c.document_id=d.id GROUP BY d.id ORDER BY d.created_at DESC").all<CompanyDocument>();
  return result.results ?? [];
}

export async function searchableChunks(includeHR: boolean): Promise<SearchableChunk[]> {
  const { db } = await ensureSchemaAndSeeds();
  const result = await db.prepare(`SELECT c.id,c.document_id AS documentId,d.title,d.department,d.owner_name AS ownerName,d.owner_email AS ownerEmail,d.audience,c.content FROM document_chunks c JOIN company_documents d ON d.id=c.document_id WHERE d.status='READY' ${includeHR ? "" : "AND d.audience='ALL_EMPLOYEES'"}`).all<SearchableChunk>();
  return result.results ?? [];
}

export async function saveDocument(file: File, metadata: { title: string; department: string; ownerName: string; ownerEmail: string; audience: DocumentAudience; uploadedBy: string }) {
  const text = await extractDocumentText(file);
  const chunks = chunkDocument(text);
  const { db, bucket } = await ensureSchemaAndSeeds();
  const id = crypto.randomUUID();
  const safeName = file.name.replace(/[^a-zA-Z0-9._-]/g, "-");
  const storageKey = `company-documents/${id}/${safeName}`;
  await bucket.put(storageKey, await file.arrayBuffer(), { httpMetadata: { contentType: file.type || "application/octet-stream" }, customMetadata: { title: metadata.title, department: metadata.department } });
  const createdAt = new Date().toISOString();
  await db.batch([
    db.prepare("INSERT INTO company_documents (id,title,filename,mime_type,department,owner_name,owner_email,audience,storage_key,extracted_text,status,uploaded_by,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)").bind(id, metadata.title, file.name, file.type || "application/octet-stream", metadata.department, metadata.ownerName, metadata.ownerEmail, metadata.audience, storageKey, text, "READY", metadata.uploadedBy, createdAt),
    ...chunks.map((content, index) => db.prepare("INSERT INTO document_chunks (id,document_id,chunk_index,content) VALUES (?,?,?,?)").bind(`${id}-${index}`, id, index, content)),
  ]);
  return { id, title: metadata.title, filename: file.name, mimeType: file.type, department: metadata.department, ownerName: metadata.ownerName, ownerEmail: metadata.ownerEmail, audience: metadata.audience, status: "READY", createdAt, chunkCount: chunks.length } satisfies CompanyDocument;
}
