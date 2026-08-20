import type { DayOneFact, Employee, FactEvent, FactValue } from "../../lib/types";

export interface DataProvider {
  getEmployees(): Promise<Employee[]>;
  getEmployee(employeeId: string): Promise<Employee | null>;
  getFacts(employeeId: string): Promise<DayOneFact[]>;
  getFactHistory(employeeId: string): Promise<FactEvent[]>;
  updateFact(employeeId: string, factKey: string, value: FactValue): Promise<void>;
  resetDemo(): Promise<void>;
}
