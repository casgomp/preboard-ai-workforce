import { authenticate, createSessionToken, defaultRoute, SESSION_COOKIE } from "../../../../services/auth/session";

export async function POST(request: Request) {
  const { email, password } = await request.json() as { email?: string; password?: string };
  if (!email || !password) return Response.json({ error: "Enter your work email and password." }, { status: 400 });
  const session = await authenticate(email, password);
  if (!session) return Response.json({ error: "Those credentials don’t match a demo account." }, { status: 401 });
  const response = Response.json({ user: session, redirectTo: defaultRoute(session) });
  const secure = new URL(request.url).protocol === "https:" ? "; Secure" : "";
  response.headers.append("Set-Cookie", `${SESSION_COOKIE}=${await createSessionToken(session)}; HttpOnly${secure}; SameSite=Lax; Path=/; Max-Age=28800`);
  return response;
}
