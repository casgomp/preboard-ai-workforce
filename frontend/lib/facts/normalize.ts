import type { DayOneFact, FactCategory, FactVisibility } from "../types";

type SourceRecord = { employeeId: string; [key: string]: string };
type Mapping = { rawKey: string; factKey: string; label: string; category: FactCategory; sourceSystem: string; ownerTeam: string; visibility: FactVisibility };

export function normalizeSourceRecords(records: SourceRecord[], mappings: Mapping[]): DayOneFact[] {
  const now = new Date().toISOString();
  return records.flatMap((record) => mappings.flatMap((mapping, index) => {
    const raw = record[mapping.rawKey];
    if (!raw) return [];
    return [{
      id: `${record.employeeId}-${mapping.factKey}-${index}`,
      employeeId: record.employeeId,
      key: mapping.factKey,
      value: raw as DayOneFact["value"],
      category: mapping.category,
      sourceSystem: mapping.sourceSystem,
      ownerTeam: mapping.ownerTeam,
      lastUpdated: now,
      visibility: mapping.visibility,
      verificationStatus: "SYSTEM_REPORTED" as const,
      candidateSafeLabel: mapping.label,
    }];
  }));
}

export const sourceMappings: Mapping[] = [
  { rawKey: "contract", factKey: "contract_status", label: "Contract", category: "HR", sourceSystem: "HR Core", ownerTeam: "People Operations", visibility: "INTERNAL" },
  { rawKey: "payroll", factKey: "payroll_status", label: "Payroll", category: "HR", sourceSystem: "HR Core", ownerTeam: "Payroll", visibility: "INTERNAL" },
  { rawKey: "employeeAccount", factKey: "employee_account", label: "Employee account", category: "IT", sourceSystem: "Identity Management", ownerTeam: "Identity & Access", visibility: "CANDIDATE_SAFE" },
  { rawKey: "laptop", factKey: "laptop_status", label: "Laptop", category: "IT", sourceSystem: "IT Asset Management", ownerTeam: "Workplace IT", visibility: "CANDIDATE_SAFE" },
  { rawKey: "softwareAccess", factKey: "software_access", label: "Software permissions", category: "IT", sourceSystem: "Access Management", ownerTeam: "Identity & Access", visibility: "CANDIDATE_SAFE" },
  { rawKey: "buildingBadge", factKey: "badge_status", label: "Building badge", category: "FACILITIES", sourceSystem: "Facilities Access", ownerTeam: "Facilities", visibility: "CANDIDATE_SAFE" },
  { rawKey: "parking", factKey: "parking_status", label: "Parking", category: "FACILITIES", sourceSystem: "Facilities Services", ownerTeam: "Facilities", visibility: "CANDIDATE_SAFE" },
  { rawKey: "welcomeMeeting", factKey: "welcome_meeting", label: "Welcome meeting", category: "MANAGER", sourceSystem: "Manager Workspace", ownerTeam: "Hiring Manager", visibility: "CANDIDATE_SAFE" },
  { rawKey: "dayOneAgenda", factKey: "day_one_agenda", label: "Day-one agenda", category: "MANAGER", sourceSystem: "Manager Workspace", ownerTeam: "Hiring Manager", visibility: "CANDIDATE_SAFE" },
  { rawKey: "orientation", factKey: "orientation_status", label: "Orientation", category: "ONBOARDING", sourceSystem: "Learning Platform", ownerTeam: "People Development", visibility: "CANDIDATE_SAFE" },
];
