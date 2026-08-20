export type FactVisibility = "INTERNAL" | "CANDIDATE_SAFE" | "CANDIDATE_ACTION_REQUIRED";
export type VerificationStatus = "VERIFIED" | "SYSTEM_REPORTED" | "STALE";
export type FactCategory = "HR" | "IT" | "FACILITIES" | "MANAGER" | "ONBOARDING";
export type FactValue = "READY" | "TEMPORARY_SOLUTION" | "IN_PROGRESS" | "DELAYED" | "BLOCKED" | "MISSING";

export type Employee = {
  id: string;
  name: string;
  role: string;
  department: string;
  location: string;
  managerName: string;
  startDate: string;
  email: string;
};

export type DayOneFact = {
  id: string;
  employeeId: string;
  key: string;
  value: FactValue;
  category: FactCategory;
  sourceSystem: string;
  ownerTeam: string;
  lastUpdated: string;
  visibility: FactVisibility;
  verificationStatus: VerificationStatus;
  previousValue?: FactValue;
  internalDetails?: string;
  candidateSafeLabel?: string;
};

export type FactEvent = {
  eventId: string;
  employeeId: string;
  factKey: string;
  previousValue?: FactValue;
  newValue: FactValue;
  sourceSystem: string;
  timestamp: string;
  label?: string;
};

export type DayOneRequirement = {
  id: string;
  factKey: string;
  name: string;
  category: FactCategory;
  ownerTeam: string;
  weight: number;
  criticalForDayOne: boolean;
};

export type ReadinessContribution = {
  requirement: DayOneRequirement;
  fact?: DayOneFact;
  earned: number;
  possible: number;
};

export type ReadinessResult = {
  score: number;
  status: "READY" | "ON_TRACK" | "AT_RISK" | "CRITICAL";
  contributions: ReadinessContribution[];
};

export type DayOneRisk = {
  id: string;
  employeeId: string;
  factKey: string;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  title: string;
  reason: string;
  ownerTeam: string;
  recommendedAction: string;
  candidateActionRequired: boolean;
};

export type EmployeeSnapshot = {
  employee: Employee;
  facts: DayOneFact[];
  history: FactEvent[];
  readiness: ReadinessResult;
  risks: DayOneRisk[];
  candidateUpdate: string;
};
