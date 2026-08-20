import { getAllSnapshots, getEmployeeSnapshot } from "../../../lib/snapshot";
import { getDataProvider } from "../../../services/data";
import { getCandidateSafeContext } from "../../../lib/privacy";
import { hasCapability, readSession } from "../../../services/auth/session";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  try {
    const session = await readSession(request.headers.get("cookie"));
    if (!session) return Response.json({ error: "Authentication required." }, { status: 401 });
    const url = new URL(request.url);
    let id = url.searchParams.get("employeeId");
    const view = url.searchParams.get("view");
    if (view === "candidate") {
      if (!hasCapability(session, "CANDIDATE") || !session.employeeId) return Response.json({ error: "Candidate access required." }, { status: 403 });
      id = session.employeeId;
    } else if (!hasCapability(session, "HR")) return Response.json({ error: "HR access required." }, { status: 403 });
    // PLAN_PR14 B6: `as_of` is trusted here the same way `/ask`'s is (D5's own
    // reasoning) — it only shifts which day risk severity is computed against, never
    // reaches log_miss or auth, so an unauthenticated-looking override carries no
    // security weight.
    const asOf = url.searchParams.get("as_of");
    const today = asOf ? new Date(`${asOf}T12:00:00`) : new Date();
    let data = id ? await getEmployeeSnapshot(id, today) : await getAllSnapshots(today);
    if (view === "candidate" && data && !Array.isArray(data)) {
      data = { ...data, facts: getCandidateSafeContext(data.facts), history: [], risks: [], readiness: { ...data.readiness, contributions: [] } };
    }
    return Response.json({ mode: process.env.DATA_MODE ?? "mock", data }, { headers: { "Cache-Control": "no-store" } });
  } catch (error) {
    return Response.json({ error: error instanceof Error ? error.message : "Unable to load Day One data." }, { status: 500 });
  }
}

export async function POST(request: Request) {
  try {
    const session = await readSession(request.headers.get("cookie"));
    if (!hasCapability(session, "HR")) return Response.json({ error: "HR access required." }, { status: session ? 403 : 401 });
    const { action } = await request.json() as { action?: string };
    const provider = getDataProvider();
    if (action === "simulate-delay") await provider.updateFact("E001", "laptop_status", "DELAYED");
    else if (action === "resolve-laptop") await provider.updateFact("E001", "laptop_status", "TEMPORARY_SOLUTION");
    else if (action === "reset") await provider.resetDemo();
    else return Response.json({ error: "Unknown demo action." }, { status: 400 });
    return Response.json({ ok: true, data: await getEmployeeSnapshot("E001") }, { headers: { "Cache-Control": "no-store" } });
  } catch (error) {
    return Response.json({ error: error instanceof Error ? error.message : "Unable to update demo state." }, { status: 500 });
  }
}
