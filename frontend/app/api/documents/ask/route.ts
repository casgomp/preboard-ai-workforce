import { readSession } from "../../../../services/auth/session";
import { getDataProvider } from "../../../../services/data";

// PR12/NOTES.md §19, B5: the candidate chat is answered by the Python brain
// (server.py) now, not services/documents/grounding.ts (deleted) — same real
// embeddings/generation/Unity-Catalog-corpus path used by app.py/cli.py.
const PYTHON_API_URL = process.env.PYTHON_API_URL ?? "http://localhost:8000";

export async function POST(request: Request) {
  const session = await readSession(request.headers.get("cookie"));
  if (!session) return Response.json({ error: "Authentication required." }, { status: 401 });

  const { question, scope = "candidate" } = (await request.json()) as {
    question?: string;
    scope?: "candidate" | "hr";
  };
  if (!question?.trim()) return Response.json({ error: "Type a question first." }, { status: 400 });
  if (question.length > 600) return Response.json({ error: "Keep questions under 600 characters." }, { status: 400 });

  // The HR document-upload/search panel (DocumentManager.tsx) is a separate
  // feature from the candidate offer-packet chat this PR wires up — the Python
  // brain is keyed by employee_id, which HR accounts don't have, and grounding.ts
  // (its only other implementation) was deleted rather than ported. Not silently
  // routing HR-scope questions into the candidate flow.
  if (scope === "hr" || !session.employeeId) {
    return Response.json(
      { error: "HR document search isn't wired to the Python brain in this build." },
      { status: 501 },
    );
  }

  const employee = await getDataProvider().getEmployee(session.employeeId);
  if (!employee) return Response.json({ error: "No employee record found for this account." }, { status: 404 });

  try {
    const response = await fetch(`${PYTHON_API_URL}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        employee_id: session.employeeId,
        question,
        start_date: employee.startDate.slice(0, 10),
      }),
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
