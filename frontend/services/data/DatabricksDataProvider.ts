import type { DayOneFact, Employee, FactCategory, FactEvent, FactValue, FactVisibility, VerificationStatus } from "../../lib/types";
import type { DataProvider } from "./DataProvider";

type StatementParameter = { name: string; value: string; type: string };
type StatementResponse = { result?: { data_array?: unknown[][] }; status?: { state?: string; error?: { message?: string } } };

// PLAN_PR13 D4/B4: column order below matches frontend/databricks/setup_tables.sql's
// CREATE TABLE column lists exactly (verified live against the workspace) — `SELECT *`
// returns positional rows in that order, so mapping is a straight destructure, not a
// name lookup. Every write goes through `parameters` (`:name` placeholders), never
// string interpolation — NOTES.md §11 already paid for the bug class where Spark SQL
// silently drops `''`-doubled quotes instead of erroring on it.
export class DatabricksDataProvider implements DataProvider {
  private config() {
    const host = process.env.DATABRICKS_HOST?.replace(/\/$/, "");
    const token = process.env.DATABRICKS_TOKEN;
    const warehouseId = process.env.DATABRICKS_HTTP_PATH?.split("/").at(-1);
    const catalog = process.env.DATABRICKS_CATALOG;
    const schema = process.env.DATABRICKS_SCHEMA;
    if (!host || !token || !warehouseId || !catalog || !schema) throw new Error("Databricks mode is selected but its server-side connection settings are incomplete.");
    return { host, token, warehouseId, catalog, schema };
  }

  private async statement(sql: string, parameters?: StatementParameter[]): Promise<StatementResponse> {
    const config = this.config();
    const response = await fetch(`${config.host}/api/2.0/sql/statements`, {
      method: "POST", headers: { Authorization: `Bearer ${config.token}`, "Content-Type": "application/json" },
      body: JSON.stringify({ warehouse_id: config.warehouseId, catalog: config.catalog, schema: config.schema, statement: sql, parameters, wait_timeout: "20s" }),
    });
    if (!response.ok) throw new Error(`Databricks request failed with status ${response.status}.`);
    const payload = await response.json() as StatementResponse;
    if (payload.status?.state === "FAILED") throw new Error(payload.status.error?.message ?? "Databricks statement failed.");
    return payload;
  }

  private rows(response: StatementResponse): string[][] {
    return (response.result?.data_array ?? []) as string[][];
  }

  private toEmployee([id, name, role, department, location, managerName, startDate, email]: string[]): Employee {
    return { id, name, role, department, location, managerName, startDate, email };
  }

  private toFact([
    id, employeeId, key, value, category, sourceSystem, ownerTeam,
    lastUpdated, visibility, verificationStatus, previousValue, internalDetails, candidateSafeLabel,
  ]: string[]): DayOneFact {
    return {
      id, employeeId, key, value: value as FactValue, category: category as FactCategory,
      sourceSystem, ownerTeam, lastUpdated, visibility: visibility as FactVisibility,
      verificationStatus: verificationStatus as VerificationStatus,
      previousValue: (previousValue ?? undefined) as FactValue | undefined,
      internalDetails: internalDetails ?? undefined,
      candidateSafeLabel: candidateSafeLabel ?? undefined,
    };
  }

  private toFactEvent([eventId, employeeId, factKey, previousValue, newValue, sourceSystem, timestamp]: string[]): FactEvent {
    return {
      eventId, employeeId, factKey, previousValue: (previousValue ?? undefined) as FactValue | undefined,
      newValue: newValue as FactValue, sourceSystem, timestamp,
    };
  }

  async getEmployees(): Promise<Employee[]> {
    const response = await this.statement("SELECT * FROM employees ORDER BY start_date");
    return this.rows(response).map((row) => this.toEmployee(row));
  }

  async getEmployee(employeeId: string): Promise<Employee | null> {
    const response = await this.statement(
      "SELECT * FROM employees WHERE employee_id = :employeeId",
      [{ name: "employeeId", value: employeeId, type: "STRING" }],
    );
    const rows = this.rows(response);
    return rows.length > 0 ? this.toEmployee(rows[0]) : null;
  }

  async getFacts(employeeId: string): Promise<DayOneFact[]> {
    const response = await this.statement(
      "SELECT * FROM day_one_facts WHERE employee_id = :employeeId",
      [{ name: "employeeId", value: employeeId, type: "STRING" }],
    );
    return this.rows(response).map((row) => this.toFact(row));
  }

  async getFactHistory(employeeId: string): Promise<FactEvent[]> {
    const response = await this.statement(
      "SELECT * FROM fact_events WHERE employee_id = :employeeId ORDER BY event_timestamp DESC",
      [{ name: "employeeId", value: employeeId, type: "STRING" }],
    );
    return this.rows(response).map((row) => this.toFactEvent(row));
  }

  async updateFact(employeeId: string, factKey: string, value: FactValue) {
    await this.statement(
      "UPDATE day_one_facts SET previous_value = fact_value, fact_value = :value, last_updated = current_timestamp() " +
        "WHERE employee_id = :employeeId AND fact_key = :factKey",
      [
        { name: "value", value, type: "STRING" },
        { name: "employeeId", value: employeeId, type: "STRING" },
        { name: "factKey", value: factKey, type: "STRING" },
      ],
    );
  }

  async resetDemo() { throw new Error("Reset Demo is intentionally available only in mock mode."); }
}
