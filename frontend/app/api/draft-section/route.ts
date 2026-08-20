import { hasCapability, readSession } from "../../../services/auth/session";

// PLAN_PR15 B6: same PYTHON_API_URL/HR-gating pattern as ../knowledge-gaps/route.ts.
const PYTHON_API_URL = process.env.PYTHON_API_URL ?? "http://localhost:8000";

export async function POST(request: Request) {
  const session = await readSession(request.headers.get("cookie"));
  if (!session) return Response.json({ error: "Authentication required." }, { status: 401 });
  if (!hasCapability(session, "HR")) return Response.json({ error: "HR access required." }, { status: 403 });

  const { question, department } = (await request.json()) as { question?: string; department?: string };
  if (!question?.trim() || !department?.trim()) {
    return Response.json({ error: "A question and department are required." }, { status: 400 });
  }

  try {
    const response = await fetch(`${PYTHON_API_URL}/draft-section`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, department }),
    });
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
