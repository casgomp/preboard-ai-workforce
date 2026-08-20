import { index, integer, sqliteTable, text } from "drizzle-orm/sqlite-core";

export const companyDocuments = sqliteTable("company_documents", {
  id: text("id").primaryKey(),
  title: text("title").notNull(),
  filename: text("filename").notNull(),
  mimeType: text("mime_type").notNull(),
  department: text("department").notNull(),
  ownerName: text("owner_name").notNull(),
  ownerEmail: text("owner_email").notNull(),
  audience: text("audience").notNull().default("ALL_EMPLOYEES"),
  storageKey: text("storage_key").notNull(),
  extractedText: text("extracted_text").notNull(),
  status: text("status").notNull().default("READY"),
  uploadedBy: text("uploaded_by").notNull(),
  createdAt: text("created_at").notNull(),
}, (table) => [index("idx_company_documents_department").on(table.department), index("idx_company_documents_audience").on(table.audience)]);

export const documentChunks = sqliteTable("document_chunks", {
  id: text("id").primaryKey(),
  documentId: text("document_id").notNull().references(() => companyDocuments.id, { onDelete: "cascade" }),
  chunkIndex: integer("chunk_index").notNull(),
  content: text("content").notNull(),
}, (table) => [index("idx_document_chunks_document_id").on(table.documentId)]);
