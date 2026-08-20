export type Capability = "CANDIDATE" | "HR";
export type AppSession = { userId: string; email: string; name: string; capabilities: Capability[]; employeeId?: string; expiresAt: number };
type DemoAccount = Omit<AppSession, "expiresAt"> & { passwordHash: string };

const accounts: DemoAccount[] = [
  { userId: "U001", email: "anna.mueller@dayone.demo", name: "Anna Müller", capabilities: ["CANDIDATE"], employeeId: "E001", passwordHash: "214963dd781c1e629f239e0cfd088104e38ec91549f45769eeee3b2edcad0726" },
  { userId: "U002", email: "sarah.weber@dayone.demo", name: "Sarah Weber", capabilities: ["HR"], passwordHash: "c670b391d1355316903c457f125d026f2f8028490a6106c6bb6733a4abffe143" },
];

export const SESSION_COOKIE = "day_one_session";
const encoder = new TextEncoder();

function base64UrlEncode(value: string | ArrayBuffer) {
  const bytes = typeof value === "string" ? encoder.encode(value) : new Uint8Array(value);
  let binary = "";
  bytes.forEach((byte) => { binary += String.fromCharCode(byte); });
  return btoa(binary).replaceAll("+", "-").replaceAll("/", "_").replaceAll("=", "");
}

function base64UrlDecode(value: string) {
  const normalized = value.replaceAll("-", "+").replaceAll("_", "/");
  const binary = atob(normalized + "=".repeat((4 - normalized.length % 4) % 4));
  return new Uint8Array([...binary].map((character) => character.charCodeAt(0)));
}

async function digest(value: string) {
  const result = await crypto.subtle.digest("SHA-256", encoder.encode(value));
  return [...new Uint8Array(result)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

// PR12/NOTES.md §19, D3/R4: the frontend session is now the auth boundary for the
// whole merged system (Python trusts the employee_id it's handed over localhost), so
// a predictable fallback secret here is a real weakness, not just a dev convenience.
// Raise instead of silently signing/verifying with a committed constant.
function requireSecret(): string {
  const secret = process.env.AUTH_SECRET;
  if (!secret) throw new Error("AUTH_SECRET is not set — refusing to sign or verify a session with a fallback secret.");
  return secret;
}

async function signature(payload: string) {
  const key = await crypto.subtle.importKey("raw", encoder.encode(requireSecret()), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  return base64UrlEncode(await crypto.subtle.sign("HMAC", key, encoder.encode(payload)));
}

async function verifySignature(payload: string, suppliedSignature: string) {
  const key = await crypto.subtle.importKey("raw", encoder.encode(requireSecret()), { name: "HMAC", hash: "SHA-256" }, false, ["verify"]);
  return crypto.subtle.verify("HMAC", key, base64UrlDecode(suppliedSignature), encoder.encode(payload));
}

export async function authenticate(email: string, password: string): Promise<AppSession | null> {
  const account = accounts.find((item) => item.email === email.trim().toLowerCase());
  if (!account || await digest(password) !== account.passwordHash) return null;
  return { userId: account.userId, email: account.email, name: account.name, capabilities: account.capabilities, employeeId: account.employeeId, expiresAt: Date.now() + 8 * 60 * 60 * 1000 };
}

export async function createSessionToken(session: AppSession) {
  const payload = base64UrlEncode(JSON.stringify(session));
  return `${payload}.${await signature(payload)}`;
}

export async function readSession(cookieHeader: string | null): Promise<AppSession | null> {
  const token = cookieHeader?.split(";").map((item) => item.trim()).find((item) => item.startsWith(`${SESSION_COOKIE}=`))?.slice(SESSION_COOKIE.length + 1);
  if (!token) return null;
  const [payload, suppliedSignature] = token.split(".");
  if (!payload || !suppliedSignature || !await verifySignature(payload, suppliedSignature)) return null;
  try {
    const session = JSON.parse(new TextDecoder().decode(base64UrlDecode(payload))) as AppSession;
    return session.expiresAt > Date.now() ? session : null;
  } catch { return null; }
}

export function hasCapability(session: AppSession | null, capability: Capability) { return Boolean(session?.capabilities.includes(capability)); }
export function defaultRoute(session: AppSession) { return session.capabilities[0] === "HR" ? "/hr" : "/candidate"; }
