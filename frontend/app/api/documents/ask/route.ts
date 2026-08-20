import { hasCapability, readSession } from "../../../../services/auth/session";
import { answerFromChunks } from "../../../../services/documents/grounding";
import { searchableChunks } from "../../../../services/documents";

export async function POST(request: Request) {
  const session = await readSession(request.headers.get("cookie"));
  if (!session) return Response.json({ error: "Authentication required." }, { status: 401 });
  const { question, scope = "candidate" } = await request.json() as { question?: string; scope?: "candidate" | "hr" };
  if (!question?.trim()) return Response.json({ error: "Type a question first." }, { status: 400 });
  if (question.length > 600) return Response.json({ error: "Keep questions under 600 characters." }, { status: 400 });
  try {
    if (scope === "hr" && !hasCapability(session, "HR")) return Response.json({ error: "HR document access required." }, { status: 403 });
    const chunks = await searchableChunks(scope === "hr");
    return Response.json(answerFromChunks(question, chunks));
  } catch (error) { return Response.json({ error: error instanceof Error ? error.message : "Unable to search company documents." }, { status: 500 }); }
}
