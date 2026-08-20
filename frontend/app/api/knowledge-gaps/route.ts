import { BackendError, backendPayload, backendRequest } from "../../../services/backend";
import { hasCapability, readSession } from "../../../services/auth/session";

export async function GET(request: Request) {
  const session = await readSession(request.headers.get("cookie"));
  if (!hasCapability(session, "HR") || !session) return Response.json({ error: "HR access required." }, { status: session ? 403 : 401 });
  try {
    const response = await backendRequest("/v1/knowledge-gaps", session, { method: "GET" });
    return Response.json(await backendPayload(response));
  } catch (error) {
    return Response.json({ error: error instanceof Error ? error.message : "Unable to load knowledge gaps." }, { status: error instanceof BackendError ? error.status : 500 });
  }
}
