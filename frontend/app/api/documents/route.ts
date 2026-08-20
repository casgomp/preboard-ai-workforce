import { hasCapability, readSession } from "../../../services/auth/session";
import { listDocuments, saveDocument } from "../../../services/documents";
import type { DocumentAudience } from "../../../services/documents/types";

export async function GET(request: Request) {
  const session = await readSession(request.headers.get("cookie"));
  if (!hasCapability(session, "HR")) return Response.json({ error: "HR access required." }, { status: session ? 403 : 401 });
  try { return Response.json({ documents: await listDocuments() }); }
  catch (error) { return Response.json({ error: error instanceof Error ? error.message : "Unable to load documents." }, { status: 500 }); }
}

export async function POST(request: Request) {
  const session = await readSession(request.headers.get("cookie"));
  if (!hasCapability(session, "HR") || !session) return Response.json({ error: "HR access required." }, { status: session ? 403 : 401 });
  try {
    const form = await request.formData();
    const file = form.get("file");
    const title = String(form.get("title") ?? "").trim();
    const department = String(form.get("department") ?? "").trim();
    const ownerName = String(form.get("ownerName") ?? "").trim();
    const ownerEmail = String(form.get("ownerEmail") ?? "").trim();
    const audience = String(form.get("audience") ?? "ALL_EMPLOYEES") as DocumentAudience;
    if (!(file instanceof File) || !title || !department || !ownerName || !ownerEmail) return Response.json({ error: "File, title, department and owner contact are required." }, { status: 400 });
    if (!["ALL_EMPLOYEES", "HR_ONLY"].includes(audience)) return Response.json({ error: "Invalid document audience." }, { status: 400 });
    return Response.json({ document: await saveDocument(file, { title, department, ownerName, ownerEmail, audience, uploadedBy: session.email }) }, { status: 201 });
  } catch (error) { return Response.json({ error: error instanceof Error ? error.message : "Document extraction failed." }, { status: 500 }); }
}
