import { describe, expect, it } from "vitest";
import { authenticate, createSessionToken, hasCapability, readSession, SESSION_COOKIE } from "../services/auth/session";
import { answerFromChunks } from "../services/documents/grounding";
import type { SearchableChunk } from "../services/documents/types";

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

describe("strict document grounding", () => {
  const chunks: SearchableChunk[] = [{ id: "c1", documentId: "d1", title: "Arrival Guide", department: "Facilities", ownerName: "Laura Stein", ownerEmail: "facilities@dayone.demo", audience: "ALL_EMPLOYEES", content: "Visitor parking is beside the North Lobby. Reception can validate your visitor pass." }];
  it("returns only supported document sentences with a citation", () => {
    const result = answerFromChunks("Where can I park?", chunks);
    expect(result.status).toBe("SUPPORTED");
    expect(result.answer).toContain("Visitor parking is beside the North Lobby.");
    expect(result.citations[0].title).toBe("Arrival Guide");
    expect(result.handoff).toBeUndefined();
  });

  it("abstains and routes to an accountable team when documents cannot answer", () => {
    const result = answerFromChunks("What food is served in the cafeteria today?", chunks);
    expect(result.status).toBe("NEEDS_HUMAN");
    expect(result.citations).toEqual([]);
    expect(result.handoff?.department).toBe("Facilities");
    expect(result.answer).toContain("couldn’t find a supported answer");
  });

  it("does not infer an HR-only answer from a weak candidate-safe match", () => {
    const safe: SearchableChunk = { ...chunks[0], id: "safe", documentId: "safe", title: "Laptop Basics", department: "Workplace IT", content: "Your laptop is provided during the morning setup session." };
    const hrOnly: SearchableChunk = { ...chunks[0], id: "hr", documentId: "hr", title: "HR Escalation", department: "People Operations", audience: "HR_ONLY", content: "The approved HR response to a delayed laptop is to reserve a temporary device." };
    expect(answerFromChunks("What is the approved HR response to a delayed laptop?", [safe]).status).toBe("NEEDS_HUMAN");
    expect(answerFromChunks("What is the approved HR response to a delayed laptop?", [safe, hrOnly])).toMatchObject({ status: "SUPPORTED", citations: [{ title: "HR Escalation" }] });
  });
});
