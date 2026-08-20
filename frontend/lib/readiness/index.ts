import { requirements as defaultRequirements } from "../requirements";
import type { DayOneFact, DayOneRequirement, FactValue, ReadinessResult } from "../types";

export const statusMultipliers: Record<FactValue, number> = {
  READY: 1,
  TEMPORARY_SOLUTION: 0.9,
  IN_PROGRESS: 0.5,
  DELAYED: 0.2,
  BLOCKED: 0,
  MISSING: 0,
};

export function calculateReadiness(facts: DayOneFact[], requirements: DayOneRequirement[] = defaultRequirements): ReadinessResult {
  const contributions = requirements.map((requirement) => {
    const fact = facts.find((item) => item.key === requirement.factKey);
    return { requirement, fact, possible: requirement.weight, earned: requirement.weight * (fact ? statusMultipliers[fact.value] : 0) };
  });
  const possible = contributions.reduce((sum, item) => sum + item.possible, 0);
  const earned = contributions.reduce((sum, item) => sum + item.earned, 0);
  const score = Math.round((earned / possible) * 100);
  const status = score >= 95 ? "READY" : score >= 80 ? "ON_TRACK" : score >= 55 ? "AT_RISK" : "CRITICAL";
  return { score, status, contributions };
}
