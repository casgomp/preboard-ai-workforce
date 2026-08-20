import { requirements as defaultRequirements } from "../requirements";
import type { DayOneFact, DayOneRequirement, DayOneRisk, Employee } from "../types";
import { daysUntilStart } from "../utils/date";

const actions: Record<string, string> = {
  laptop_status: "Reserve a temporary laptop",
  badge_status: "Request temporary building access",
  welcome_meeting: "Ask the manager to schedule a welcome session",
  employee_account: "Escalate account provisioning",
  software_access: "Prioritize required software permissions",
  contract_status: "Escalate contract completion to People Operations",
};

const titles: Record<string, string> = {
  laptop_status: "Equipment readiness risk",
  badge_status: "Workplace access risk",
  welcome_meeting: "Manager welcome risk",
  employee_account: "Account readiness risk",
  software_access: "Software access risk",
};

export function detectRisks(employee: Employee, facts: DayOneFact[], requirements: DayOneRequirement[] = defaultRequirements, today: Date = new Date()): DayOneRisk[] {
  const days = daysUntilStart(employee.startDate, today);
  return requirements.flatMap((requirement) => {
    const fact = facts.find((item) => item.key === requirement.factKey);
    if (!fact || fact.value === "READY" || fact.value === "TEMPORARY_SOLUTION") return [];
    let severity: DayOneRisk["severity"] = "LOW";
    if (requirement.criticalForDayOne && ["BLOCKED", "MISSING"].includes(fact.value) && days <= 3) severity = "CRITICAL";
    else if (requirement.criticalForDayOne && fact.value === "DELAYED" && days <= 7) severity = "HIGH";
    else if (fact.value === "DELAYED" || (requirement.criticalForDayOne && days <= 7)) severity = "MEDIUM";
    return [{
      id: `risk-${employee.id}-${fact.key}`,
      employeeId: employee.id,
      factKey: fact.key,
      severity,
      title: titles[fact.key] ?? `${requirement.name} needs attention`,
      reason: `${requirement.name} is ${fact.value.toLowerCase().replaceAll("_", " ")} and ${employee.name.split(" ")[0]} ${days >= 0 ? `starts in ${days} days` : `started ${-days} days ago`}.`,
      ownerTeam: fact.ownerTeam,
      recommendedAction: actions[fact.key] ?? `Confirm a completion plan with ${fact.ownerTeam}`,
      candidateActionRequired: fact.visibility === "CANDIDATE_ACTION_REQUIRED",
    }];
  });
}
