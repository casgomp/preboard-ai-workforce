import { describe, expect, it } from "vitest";
import { authenticate, createSessionToken, hasCapability, readSession, SESSION_COOKIE } from "../services/auth/session";

describe("capability-based authentication", () => {
  it("assigns each account exactly one workspace", async () => {
    const candidate = await authenticate("anna.mueller@dayone.demo", "Welcome5!");
    const hr = await authenticate("sarah.weber@dayone.demo", "PeopleOps!");
    expect(hasCapability(candidate, "CANDIDATE")).toBe(true);
    expect(hasCapability(candidate, "HR")).toBe(false);
    expect(candidate?.capabilities).toEqual(["CANDIDATE"]);
    expect(hasCapability(hr, "HR")).toBe(true);
    expect(hr?.employeeId).toBeUndefined();
    expect(hr?.capabilities).toEqual(["HR"]);
    expect(await authenticate("unknown@dayone.demo", "not-a-demo-password")).toBeNull();
  });

  it("signs and validates the server session cookie", async () => {
    const session = await authenticate("anna.mueller@dayone.demo", "Welcome5!");
    const token = await createSessionToken(session!);
    expect(await readSession(`${SESSION_COOKIE}=${token}`)).toMatchObject({ userId: "U001", employeeId: "E001" });
    expect(await readSession(`${SESSION_COOKIE}=${token}tampered`)).toBeNull();
  });
});

describe("AUTH_SECRET fallback removed (PR12/NOTES.md §19, D3/R4)", () => {
  it("refuses to sign a session without AUTH_SECRET set", async () => {
    const original = process.env.AUTH_SECRET;
    delete process.env.AUTH_SECRET;
    try {
      await expect(authenticate("anna.mueller@dayone.demo", "Welcome5!").then((s) => createSessionToken(s!))).rejects.toThrow(
        /AUTH_SECRET/,
      );
    } finally {
      process.env.AUTH_SECRET = original;
    }
  });
});
