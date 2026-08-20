import { calculateReadiness } from "./readiness";
import { detectRisks } from "./risk";
import { getCandidateSafeContext } from "./privacy";
import { getAIService } from "../services/ai";
import { getDataProvider } from "../services/data";
import type { EmployeeSnapshot } from "./types";

const severityOrder = { CRITICAL: 4, HIGH: 3, MEDIUM: 2, LOW: 1 };

export async function getEmployeeSnapshot(employeeId: string): Promise<EmployeeSnapshot | null> {
  const provider = getDataProvider();
  const employee = await provider.getEmployee(employeeId);
  if (!employee) return null;
  const [facts, history] = await Promise.all([provider.getFacts(employeeId), provider.getFactHistory(employeeId)]);
  const readiness = calculateReadiness(facts);
  const risks = detectRisks(employee, facts).sort((a, b) => severityOrder[b.severity] - severityOrder[a.severity]);
  const visibleFacts = getCandidateSafeContext(facts);
  const candidateUpdate = await getAIService().generateCandidateUpdate({ employee, readiness, visibleFacts, candidateActionRequired: visibleFacts.some((fact) => fact.visibility === "CANDIDATE_ACTION_REQUIRED") });
  return { employee, facts, history, readiness, risks, candidateUpdate };
}

export async function getAllSnapshots() {
  const employees = await getDataProvider().getEmployees();
  return Promise.all(employees.map((employee) => getEmployeeSnapshot(employee.id))) as Promise<EmployeeSnapshot[]>;
}
