import type { DayOneFact, Employee, FactCategory, FactEvent, FactValue, FactVisibility } from "../../lib/types";
import { dateInDays } from "../../lib/utils/date";

export const employees: Employee[] = [
  ["E001", "Anna Müller", "Software Engineer", "Digital Engineering", "Wolfsburg", "Sarah Weber", 5],
  ["E002", "David Klein", "Product Manager", "Product Strategy", "Berlin", "Nina Hoffmann", 3],
  ["E003", "Maria Rossi", "Data Engineer", "Data Platforms", "Munich", "Jonas Bauer", 8],
  ["E004", "Lukas Schmidt", "UX Designer", "Design", "Wolfsburg", "Lea König", 1],
  ["E005", "Sofia Garcia", "Data Analyst", "Business Intelligence", "Berlin", "David Neumann", 12],
  ["E006", "Noah Fischer", "Cloud Engineer", "Platform", "Munich", "Mia Vogel", 2],
  ["E007", "Elena Novak", "QA Engineer", "Quality", "Wolfsburg", "Sarah Weber", 6],
  ["E008", "Amir Haddad", "Security Analyst", "Cybersecurity", "Berlin", "Paul Krüger", 9],
  ["E009", "Julia Meier", "Finance Partner", "Finance", "Munich", "Eva Richter", 11],
  ["E010", "Mateo Silva", "Scrum Master", "Delivery", "Wolfsburg", "Lea König", 4],
  ["E011", "Hannah Wolf", "Legal Counsel", "Legal", "Berlin", "Nina Hoffmann", 13],
  ["E012", "Theo Wagner", "ML Engineer", "Applied AI", "Munich", "Jonas Bauer", 7],
].map(([id, name, role, department, location, managerName, days]) => ({
  id: String(id), name: String(name), role: String(role), department: String(department), location: String(location), managerName: String(managerName),
  startDate: dateInDays(Number(days)), email: `${String(name).toLowerCase().replaceAll(" ", ".").replaceAll("ü", "u")}@example.demo`,
}));

const definitions: Array<[string, string, FactCategory, string, string, FactVisibility]> = [
  ["contract_status", "Contract", "HR", "HR Core", "People Operations", "INTERNAL"],
  ["payroll_status", "Payroll", "HR", "HR Core", "Payroll", "INTERNAL"],
  ["manager_assigned", "Manager assignment", "HR", "HR Core", "People Operations", "CANDIDATE_SAFE"],
  ["employee_account", "Employee account", "IT", "Identity Management", "Identity & Access", "CANDIDATE_SAFE"],
  ["laptop_status", "Laptop", "IT", "IT Asset Management", "Workplace IT", "CANDIDATE_SAFE"],
  ["software_access", "Software permissions", "IT", "Access Management", "Identity & Access", "CANDIDATE_SAFE"],
  ["badge_status", "Building badge", "FACILITIES", "Facilities Access", "Facilities", "CANDIDATE_SAFE"],
  ["parking_status", "Parking", "FACILITIES", "Facilities Services", "Facilities", "CANDIDATE_SAFE"],
  ["welcome_meeting", "Welcome meeting", "MANAGER", "Manager Workspace", "Hiring Manager", "CANDIDATE_SAFE"],
  ["day_one_agenda", "Day-one agenda", "MANAGER", "Manager Workspace", "Hiring Manager", "CANDIDATE_SAFE"],
  ["orientation_status", "Orientation", "ONBOARDING", "Learning Platform", "People Development", "CANDIDATE_SAFE"],
];

const overrides: Record<string, Record<string, FactValue>> = {
  E001: { parking_status: "IN_PROGRESS" },
  E002: { badge_status: "DELAYED" },
  E003: { parking_status: "IN_PROGRESS", orientation_status: "IN_PROGRESS" },
  E005: { parking_status: "IN_PROGRESS", orientation_status: "IN_PROGRESS" },
  E006: { laptop_status: "BLOCKED" },
  E012: { software_access: "DELAYED" },
};

export function createSeedFacts(): DayOneFact[] {
  return employees.flatMap((employee) => definitions.map(([key, label, category, sourceSystem, ownerTeam, visibility], index) => ({
    id: `${employee.id}-${String(index + 1).padStart(2, "0")}`,
    employeeId: employee.id,
    key,
    value: overrides[employee.id]?.[key] ?? "READY",
    category,
    sourceSystem,
    ownerTeam,
    lastUpdated: new Date(Date.now() - index * 24 * 60 * 1000).toISOString(),
    visibility,
    verificationStatus: index % 3 === 0 ? "VERIFIED" : "SYSTEM_REPORTED",
    candidateSafeLabel: label,
    internalDetails: key === "parking_status" && employee.id === "E001" ? "Parking permit processing is within the normal preparation window." : undefined,
  })));
}

export function createSeedHistory(): FactEvent[] {
  const now = Date.now();
  return [
    { eventId: "H001", employeeId: "E001", factKey: "employee_account", newValue: "READY", sourceSystem: "Identity Management", timestamp: new Date(now - 3 * 3_600_000).toISOString(), label: "Employee account confirmed ready" },
    { eventId: "H002", employeeId: "E001", factKey: "badge_status", newValue: "READY", sourceSystem: "Facilities Access", timestamp: new Date(now - 2 * 3_600_000).toISOString(), label: "Building access confirmed" },
    { eventId: "H003", employeeId: "E001", factKey: "welcome_meeting", newValue: "READY", sourceSystem: "Manager Workspace", timestamp: new Date(now - 1 * 3_600_000).toISOString(), label: "Manager welcome meeting scheduled" },
  ];
}
