import type { AppSession } from "./auth/session";

const BACKEND_URL = process.env.PREBOARD_API_URL ?? "http://127.0.0.1:8000";
const SERVICE_KEY = process.env.PREBOARD_API_SECRET ?? "preboard-local-api-secret";

export class BackendError extends Error {
  constructor(message: string, public status: number) { super(message); }
}

export async function backendRequest(path: string, session: AppSession, init: RequestInit = {}) {
  const headers = new Headers(init.headers);
  headers.set("X-Preboard-Service-Key", SERVICE_KEY);
  headers.set("X-Preboard-Role", session.capabilities[0]);
  headers.set("X-Preboard-Subject", session.employeeId ?? session.email);
  try {
    return await fetch(`${BACKEND_URL}${path}`, { ...init, headers, cache: "no-store" });
  } catch {
    throw new Error("The Preboard Python API is unavailable. Start it on port 8000 and try again.");
  }
}

export async function backendPayload(response: Response) {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new BackendError(payload.detail ?? payload.error ?? "The Preboard Python API request failed.", response.status);
  return payload;
}
