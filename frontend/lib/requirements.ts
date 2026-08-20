import type { DayOneRequirement } from "./types";

export const requirements: DayOneRequirement[] = [
  { id: "R01", factKey: "contract_status", name: "Contract", category: "HR", ownerTeam: "People Operations", weight: 5, criticalForDayOne: true },
  { id: "R02", factKey: "payroll_status", name: "Payroll", category: "HR", ownerTeam: "Payroll", weight: 2, criticalForDayOne: false },
  { id: "R03", factKey: "employee_account", name: "Employee account", category: "IT", ownerTeam: "Identity & Access", weight: 8, criticalForDayOne: true },
  { id: "R04", factKey: "laptop_status", name: "Laptop", category: "IT", ownerTeam: "Workplace IT", weight: 20, criticalForDayOne: true },
  { id: "R05", factKey: "software_access", name: "Software permissions", category: "IT", ownerTeam: "Identity & Access", weight: 4, criticalForDayOne: true },
  { id: "R06", factKey: "badge_status", name: "Building badge", category: "FACILITIES", ownerTeam: "Facilities", weight: 4, criticalForDayOne: true },
  { id: "R07", factKey: "manager_assigned", name: "Manager assignment", category: "HR", ownerTeam: "People Operations", weight: 2, criticalForDayOne: true },
  { id: "R08", factKey: "welcome_meeting", name: "Welcome meeting", category: "MANAGER", ownerTeam: "Hiring Manager", weight: 2, criticalForDayOne: true },
  { id: "R09", factKey: "day_one_agenda", name: "Day-one agenda", category: "MANAGER", ownerTeam: "Hiring Manager", weight: 3, criticalForDayOne: true },
  { id: "R10", factKey: "orientation_status", name: "Orientation", category: "ONBOARDING", ownerTeam: "People Development", weight: 2, criticalForDayOne: false },
  { id: "R11", factKey: "parking_status", name: "Parking", category: "FACILITIES", ownerTeam: "Facilities", weight: 5, criticalForDayOne: false },
];
