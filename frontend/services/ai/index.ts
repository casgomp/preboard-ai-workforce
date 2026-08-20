import type { AIService } from "./AIService";
import { DatabricksAIService } from "./DatabricksAIService";
import { MockAIService } from "./MockAIService";

let service: AIService | undefined;
export function getAIService() {
  service ??= process.env.AI_MODE === "databricks" ? new DatabricksAIService() : new MockAIService();
  return service;
}
