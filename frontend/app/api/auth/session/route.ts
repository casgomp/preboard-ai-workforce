import { readSession } from "../../../../services/auth/session";

export async function GET(request: Request) {
  const session = await readSession(request.headers.get("cookie"));
  return session ? Response.json({ authenticated: true, user: session }) : Response.json({ authenticated: false }, { status: 401 });
}
