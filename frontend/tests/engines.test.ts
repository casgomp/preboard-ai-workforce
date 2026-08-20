import { beforeEach, describe, expect, it } from "vitest";
import { createSeedFacts, employees } from "../data/demo/seed";
import { normalizeSourceRecords, sourceMappings } from "../lib/facts/normalize";
import { getCandidateSafeContext } from "../lib/privacy";
import { calculateReadiness } from "../lib/readiness";
import { detectRisks } from "../lib/risk";
import type { DayOneFact } from "../lib/types";
import { clearDemoStoreForTests, MockDataProvider } from "../services/data/MockDataProvider";

function factsFor(id: string) { return createSeedFacts().filter((fact) => fact.employeeId === id); }

describe("readiness engine", () => {
  it("returns high readiness when major facts are ready", () => {
    const result = calculateReadiness(factsFor("E001"));
    expect(result.score).toBeGreaterThanOrEqual(95);
  });
  it("drops when the laptop is delayed and recovers with a temporary solution", () => {
    const facts = factsFor("E001");
    const base = calculateReadiness(facts).score;
    const laptop = facts.find((fact) => fact.key === "laptop_status")!;
    laptop.value = "DELAYED";
    const delayed = calculateReadiness(facts).score;
    laptop.value = "TEMPORARY_SOLUTION";
    const temporary = calculateReadiness(facts).score;
    expect(delayed).toBeLessThan(base);
    expect(temporary).toBeGreaterThan(delayed);
    expect(temporary).toBeGreaterThanOrEqual(90);
  });
});

describe("risk engine", () => {
  it("marks a blocked critical fact within three days CRITICAL", () => {
    const employee = employees.find((item) => item.id === "E006")!;
    expect(detectRisks(employee, factsFor("E006")).some((risk) => risk.severity === "CRITICAL")).toBe(true);
  });
  it("marks a delayed critical fact within seven days HIGH", () => {
    const employee = employees.find((item) => item.id === "E002")!;
    expect(detectRisks(employee, factsFor("E002")).some((risk) => risk.severity === "HIGH")).toBe(true);
  });
});

describe("candidate privacy boundary", () => {
  const fact = (visibility: DayOneFact["visibility"]): DayOneFact => ({ id: visibility, employeeId: "E001", key: visibility, value: "READY", category: "HR", sourceSystem: "test", ownerTeam: "test", lastUpdated: new Date().toISOString(), visibility, verificationStatus: "VERIFIED" });
  it("excludes internal facts and includes both candidate visibility modes", () => {
    const result = getCandidateSafeContext([fact("INTERNAL"), fact("CANDIDATE_SAFE"), fact("CANDIDATE_ACTION_REQUIRED")]);
    expect(result.map((item) => item.visibility)).toEqual(["CANDIDATE_SAFE", "CANDIDATE_ACTION_REQUIRED"]);
  });
});

describe("normalization", () => {
  it("turns source fields into provenance-rich facts", () => {
    const result = normalizeSourceRecords([{ employeeId: "E001", laptop: "READY" }], sourceMappings);
    expect(result[0]).toMatchObject({ key: "laptop_status", sourceSystem: "IT Asset Management", ownerTeam: "Workplace IT" });
  });
});

describe("repeatable demo state", () => {
  beforeEach(() => clearDemoStoreForTests());
  it("moves READY → DELAYED → TEMPORARY_SOLUTION and reset restores READY", async () => {
    const provider = new MockDataProvider();
    const value = async () => (await provider.getFacts("E001")).find((fact) => fact.key === "laptop_status")!.value;
    expect(await value()).toBe("READY");
    await provider.updateFact("E001", "laptop_status", "DELAYED");
    expect(await value()).toBe("DELAYED");
    await provider.updateFact("E001", "laptop_status", "TEMPORARY_SOLUTION");
    expect(await value()).toBe("TEMPORARY_SOLUTION");
    await provider.resetDemo();
    expect(await value()).toBe("READY");
  });
});
