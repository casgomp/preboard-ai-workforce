import { hasCapability, readSession } from "../../../services/auth/session";
import { BackendError, backendPayload, backendRequest } from "../../../services/backend";

export async function GET(request: Request) {
  const session = await readSession(request.headers.get("cookie"));
  if (!hasCapability(session, "HR")) return Response.json({ error: "HR access required." }, { status: session ? 403 : 401 });
  try {
    const response = await backendRequest("/v1/documents", session!, { method: "GET" });
    return Response.json(await backendPayload(response));
  }
  catch (error) { return Response.json({ error: error instanceof Error ? error.message : "Unable to load documents." }, { status: error instanceof BackendError ? error.status : 500 }); }
}

export async function POST(request: Request) {
  const session = await readSession(request.headers.get("cookie"));
  if (!hasCapability(session, "HR") || !session) return Response.json({ error: "HR access required." }, { status: session ? 403 : 401 });
  try {
    const form = await request.formData();
    const response = await backendRequest("/v1/documents", session, { method: "POST", body: form });
    return Response.json(await backendPayload(response), { status: 201 });
  } catch (error) { return Response.json({ error: error instanceof Error ? error.message : "Document extraction failed." }, { status: error instanceof BackendError ? error.status : 500 }); }
}
