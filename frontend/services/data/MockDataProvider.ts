import { createSeedFacts, createSeedHistory, employees } from "../../data/demo/seed";
import type { DayOneFact, FactEvent, FactValue } from "../../lib/types";
import type { DataProvider } from "./DataProvider";

type DemoStore = { facts: DayOneFact[]; history: FactEvent[] };
const globalStore = globalThis as typeof globalThis & { __dayOneDemoStore?: DemoStore };

function store() {
  globalStore.__dayOneDemoStore ??= { facts: createSeedFacts(), history: createSeedHistory() };
  return globalStore.__dayOneDemoStore;
}

export class MockDataProvider implements DataProvider {
  async getEmployees() { return employees; }
  async getEmployee(employeeId: string) { return employees.find((employee) => employee.id === employeeId) ?? null; }
  async getFacts(employeeId: string) { return store().facts.filter((fact) => fact.employeeId === employeeId); }
  async getFactHistory(employeeId: string) { return store().history.filter((event) => event.employeeId === employeeId).sort((a, b) => b.timestamp.localeCompare(a.timestamp)); }

  async updateFact(employeeId: string, factKey: string, value: FactValue) {
    const state = store();
    const fact = state.facts.find((item) => item.employeeId === employeeId && item.key === factKey);
    if (!fact) throw new Error(`Fact ${factKey} not found for ${employeeId}`);
    if (fact.value === value) return;
    const previousValue = fact.value;
    fact.previousValue = previousValue;
    fact.value = value;
    fact.lastUpdated = new Date().toISOString();
    fact.verificationStatus = "SYSTEM_REPORTED";
    if (factKey === "laptop_status" && value === "DELAYED") {
      fact.internalDetails = "Vendor shipment delayed. Temporary inventory may be available.";
    } else if (factKey === "laptop_status" && value === "TEMPORARY_SOLUTION") {
      fact.internalDetails = "Temporary device assigned and ready for collection.";
    }
    state.history.unshift({
      eventId: crypto.randomUUID(), employeeId, factKey, previousValue, newValue: value,
      sourceSystem: value === "TEMPORARY_SOLUTION" ? "Workplace IT" : fact.sourceSystem,
      timestamp: fact.lastUpdated,
      label: value === "TEMPORARY_SOLUTION" ? "Temporary device assigned" : `${fact.candidateSafeLabel ?? factKey} changed`,
    });
  }

  async resetDemo() {
    globalStore.__dayOneDemoStore = { facts: createSeedFacts(), history: createSeedHistory() };
  }
}

export function clearDemoStoreForTests() { delete globalStore.__dayOneDemoStore; }
