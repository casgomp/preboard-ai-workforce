import type { DayOneFact, FactEvent } from "../types";

export function getCandidateSafeContext(facts: DayOneFact[]) {
  return facts.filter((fact) => fact.visibility === "CANDIDATE_SAFE" || fact.visibility === "CANDIDATE_ACTION_REQUIRED");
}

// PLAN_PR15 B5: filtered on the fact's own visibility, not on `event.label` text —
// a label alone could read as harmless while its underlying fact isn't
// candidate-safe (e.g. a payroll amount mentioned in passing), so the check goes
// through the same source of truth `getCandidateSafeContext` already uses.
export function getCandidateSafeHistory(history: FactEvent[], facts: DayOneFact[]): FactEvent[] {
  const safeKeys = new Set(getCandidateSafeContext(facts).map((fact) => fact.key));
  return history.filter((event) => safeKeys.has(event.factKey));
}
