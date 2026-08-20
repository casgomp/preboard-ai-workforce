import type { DataProvider } from "./DataProvider";
import { DatabricksDataProvider } from "./DatabricksDataProvider";
import { MockDataProvider } from "./MockDataProvider";

let provider: DataProvider | undefined;
export function getDataProvider() {
  provider ??= process.env.DATA_MODE === "databricks" ? new DatabricksDataProvider() : new MockDataProvider();
  return provider;
}
