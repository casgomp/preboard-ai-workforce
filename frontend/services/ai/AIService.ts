import type { DayOneFact, DayOneRisk, Employee, ReadinessResult } from "../../lib/types";
export type CandidateAIContext = { employee: Employee; readiness: ReadinessResult; visibleFacts: DayOneFact[]; candidateActionRequired: boolean };
export type HRAIContext = { employee: Employee; readiness: ReadinessResult; facts: DayOneFact[]; risks: DayOneRisk[] };

export interface AIService {
  generateCandidateUpdate(context: CandidateAIContext): Promise<string>;
  generateHRRecommendation(context: HRAIContext): Promise<string>;
}
