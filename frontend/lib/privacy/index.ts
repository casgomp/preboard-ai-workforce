import type { DayOneFact } from "../types";

export function getCandidateSafeContext(facts: DayOneFact[]) {
  return facts.filter((fact) => fact.visibility === "CANDIDATE_SAFE" || fact.visibility === "CANDIDATE_ACTION_REQUIRED");
}
