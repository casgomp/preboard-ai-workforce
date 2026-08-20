import type { AIService, CandidateAIContext, HRAIContext } from "./AIService";

export class MockAIService implements AIService {
  async generateCandidateUpdate(context: CandidateAIContext) {
    const laptop = context.visibleFacts.find((fact) => fact.key === "laptop_status");
    const action = context.visibleFacts.find((fact) => fact.visibility === "CANDIDATE_ACTION_REQUIRED" && ["MISSING", "BLOCKED"].includes(fact.value));
    if (action) return `We still need one item from you: ${action.candidateSafeLabel ?? "a required document"}. Please complete it before your first day.`;
    if (laptop?.value === "DELAYED") return "We’re finalizing your equipment setup. Your account, workplace access and first-day schedule are already prepared. No action is required from you right now.";
    if (laptop?.value === "TEMPORARY_SOLUTION") return "Great news — everything required for your first day is ready. We look forward to welcoming you.";
    return "Everything is on track for your first day. Your account, workplace access, equipment and schedule are being prepared.";
  }

  async generateHRRecommendation(context: HRAIContext) {
    const risk = context.risks[0];
    if (!risk) return `${context.employee.name} is on track. Continue monitoring normal preparation signals.`;
    return `${context.employee.name.split(" ")[0]} starts soon and ${risk.reason.split(" and ")[0].toLowerCase()}. ${risk.recommendedAction} to protect the Day One experience.`;
  }

}
