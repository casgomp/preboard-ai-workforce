import { calculateReadiness } from "./readiness";
import { detectRisks } from "./risk";
import { getCandidateSafeContext } from "./privacy";
import { getAIService } from "../services/ai";
import { getDataProvider } from "../services/data";
import type { EmployeeSnapshot } from "./types";

const severityOrder = { CRITICAL: 4, HIGH: 3, MEDIUM: 2, LOW: 1 };

// PLAN_PR14 B6: `today` drives risk severity thresholds (which are day-count-based),
// not readiness or facts themselves — defaults to the real clock so every existing
// caller is unaffected. The HR board runs on MockDataProvider (NOTES §2); scrubbing
// moves risk derived from mock facts, which is honest as a mechanism demo and not
// meant to be narrated as live data.
export async function getEmployeeSnapshot(employeeId: string, today: Date = new Date()): Promise<EmployeeSnapshot | null> {
  const provider = getDataProvider();
  const employee = await provider.getEmployee(employeeId);
  if (!employee) return null;
  const [facts, history] = await Promise.all([provider.getFacts(employeeId), provider.getFactHistory(employeeId)]);
  const readiness = calculateReadiness(facts);
  const risks = detectRisks(employee, facts, undefined, today).sort((a, b) => severityOrder[b.severity] - severityOrder[a.severity]);
  const visibleFacts = getCandidateSafeContext(facts);
  const candidateUpdate = await getAIService().generateCandidateUpdate({ employee, readiness, visibleFacts, candidateActionRequired: visibleFacts.some((fact) => fact.visibility === "CANDIDATE_ACTION_REQUIRED") });
  return { employee, facts, history, readiness, risks, candidateUpdate };
}

export async function getAllSnapshots(today: Date = new Date()) {
  const employees = await getDataProvider().getEmployees();
  return Promise.all(employees.map((employee) => getEmployeeSnapshot(employee.id, today))) as Promise<EmployeeSnapshot[]>;
}
