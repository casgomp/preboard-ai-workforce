export type DocumentAudience = "ALL_EMPLOYEES" | "HR_ONLY";
export type CompanyDocument = { id: string; title: string; filename: string; mimeType: string; department: string; ownerName: string; ownerEmail: string; audience: DocumentAudience; status: string; createdAt: string; chunkCount?: number };
export type GroundedAnswer = {
  status: "SUPPORTED" | "NEEDS_HUMAN";
  answer: string;
  citations: Array<{ documentId: string; title: string; excerpt: string }>;
  handoff?: { department: string; person: string; email: string };
};
