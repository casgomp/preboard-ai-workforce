import { hasCapability, readSession } from "../../../../services/auth/session";
import { BackendError, backendPayload, backendRequest } from "../../../../services/backend";

export async function POST(request: Request) {
  const session = await readSession(request.headers.get("cookie"));
  if (!session) return Response.json({ error: "Authentication required." }, { status: 401 });
  const { question, scope = "candidate" } = await request.json() as { question?: string; scope?: "candidate" | "hr" };
  if (!question?.trim()) return Response.json({ error: "Type a question first." }, { status: 400 });
  if (question.length > 600) return Response.json({ error: "Keep questions under 600 characters." }, { status: 400 });
  try {
    const requiredCapability = scope === "hr" ? "HR" : "CANDIDATE";
    if (!hasCapability(session, requiredCapability)) return Response.json({ error: `${scope === "hr" ? "HR" : "Candidate"} document access required.` }, { status: 403 });
    const response = await backendRequest("/v1/questions", session, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question, scope }) });
    return Response.json(await backendPayload(response));
  } catch (error) { return Response.json({ error: error instanceof Error ? error.message : "Unable to search company documents." }, { status: error instanceof BackendError ? error.status : 500 }); }
}
