import { hasCapability, readSession } from "../../../services/auth/session";

// Ported from feature/fused-preboard's KnowledgeGapPanel/route, adapted to call
// server.py directly (same PYTHON_API_URL pattern as ../documents/ask/route.ts)
// instead of that branch's separate api/main.py + service-key backend.ts.
const PYTHON_API_URL = process.env.PYTHON_API_URL ?? "http://localhost:8000";

export async function GET(request: Request) {
  const session = await readSession(request.headers.get("cookie"));
  if (!session) return Response.json({ error: "Authentication required." }, { status: 401 });
  if (!hasCapability(session, "HR")) return Response.json({ error: "HR access required." }, { status: 403 });

  try {
    const response = await fetch(`${PYTHON_API_URL}/knowledge-gaps`, { cache: "no-store" });
    if (!response.ok) {
      return Response.json(
        { error: `The document assistant returned an error (${response.status}).` },
        { status: 502 },
      );
    }
    return Response.json(await response.json());
  } catch {
    return Response.json(
      { error: "Unable to reach the document assistant. Is the Python server running (uvicorn server:app)?" },
      { status: 502 },
    );
  }
}
