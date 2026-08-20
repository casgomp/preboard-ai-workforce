export type DocumentAudience = "ALL_EMPLOYEES" | "HR_ONLY";
export type CompanyDocument = { id: string; title: string; filename: string; mimeType: string; department: string; ownerName: string; ownerEmail: string; audience: DocumentAudience; status: string; createdAt: string; chunkCount?: number };
export type SearchableChunk = { id: string; documentId: string; title: string; department: string; ownerName: string; ownerEmail: string; audience: DocumentAudience; content: string };
export type GroundedAnswer = {
  status: "SUPPORTED" | "NEEDS_HUMAN";
  answer: string;
  citations: Array<{ documentId: string; title: string; excerpt: string }>;
  handoff?: { department: string; person: string; email: string };
  // PLAN_PR14 B4: short "asked at" chip, e.g. "T-40 · 2-8 weeks out" — absent when
  // there was no start_date to band against.
  askedAt?: string | null;
};
