import { SESSION_COOKIE } from "../../../../services/auth/session";

export async function POST() {
  const response = Response.json({ ok: true });
  response.headers.append("Set-Cookie", `${SESSION_COOKIE}=; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=0`);
  return response;
}
