import type { DayOneFact, Employee, FactEvent, FactValue } from "../../lib/types";
import type { DataProvider } from "./DataProvider";

type StatementResponse = { result?: { data_array?: unknown[][] }; status?: { state?: string; error?: { message?: string } } };

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

  private async statement(sql: string): Promise<StatementResponse> {
    const config = this.config();
    const response = await fetch(`${config.host}/api/2.0/sql/statements`, {
      method: "POST", headers: { Authorization: `Bearer ${config.token}`, "Content-Type": "application/json" },
      body: JSON.stringify({ warehouse_id: config.warehouseId, catalog: config.catalog, schema: config.schema, statement: sql, wait_timeout: "20s" }),
    });
    if (!response.ok) throw new Error(`Databricks request failed with status ${response.status}.`);
    const payload = await response.json() as StatementResponse;
    if (payload.status?.state === "FAILED") throw new Error(payload.status.error?.message ?? "Databricks statement failed.");
    return payload;
  }

  async getEmployees(): Promise<Employee[]> { await this.statement("SELECT * FROM employees ORDER BY start_date"); throw new Error("Map your workspace result schema in DatabricksDataProvider before production use."); }
  async getEmployee(employeeId: string): Promise<Employee | null> { const all = await this.getEmployees(); return all.find((item) => item.id === employeeId) ?? null; }
  async getFacts(employeeId: string): Promise<DayOneFact[]> { await this.statement(`SELECT * FROM day_one_facts WHERE employee_id = '${employeeId.replaceAll("'", "''")}'`); throw new Error("Map your workspace result schema in DatabricksDataProvider before production use."); }
  async getFactHistory(employeeId: string): Promise<FactEvent[]> { await this.statement(`SELECT * FROM fact_events WHERE employee_id = '${employeeId.replaceAll("'", "''")}' ORDER BY event_timestamp DESC`); throw new Error("Map your workspace result schema in DatabricksDataProvider before production use."); }
  async updateFact(employeeId: string, factKey: string, value: FactValue) { await this.statement(`UPDATE day_one_facts SET previous_value = fact_value, fact_value = '${value}', last_updated = current_timestamp() WHERE employee_id = '${employeeId.replaceAll("'", "''")}' AND fact_key = '${factKey.replaceAll("'", "''")}'`); }
  async resetDemo() { throw new Error("Reset Demo is intentionally available only in mock mode."); }
}
