import { MockAIService } from "./MockAIService";
import type { AIService, CandidateAIContext, HRAIContext } from "./AIService";

export class DatabricksAIService implements AIService {
  private fallback = new MockAIService();

  private async invoke(messages: Array<{ role: string; content: string }>) {
    const host = process.env.DATABRICKS_HOST?.replace(/\/$/, "");
    const token = process.env.DATABRICKS_TOKEN;
    const endpoint = process.env.DATABRICKS_MODEL_ENDPOINT;
    if (!host || !token || !endpoint) throw new Error("Databricks model serving is not fully configured.");
    const response = await fetch(`${host}/serving-endpoints/${endpoint}/invocations`, {
      method: "POST", headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify({ messages, temperature: 0.1, max_tokens: 250 }),
    });
    if (!response.ok) throw new Error(`Model endpoint returned ${response.status}.`);
    const payload = await response.json() as { choices?: Array<{ message?: { content?: string } }> };
    const content = payload.choices?.[0]?.message?.content;
    if (!content) throw new Error("Model endpoint returned no answer.");
    return content;
  }

  async generateCandidateUpdate(context: CandidateAIContext) {
    try { return await this.invoke([{ role: "system", content: "Write one calm candidate update using only supplied candidate-visible facts. Never invent policy or operational causes." }, { role: "user", content: JSON.stringify(context) }]); }
    catch { return this.fallback.generateCandidateUpdate(context); }
  }
  async generateHRRecommendation(context: HRAIContext) {
    try { return await this.invoke([{ role: "system", content: "Write one concise HR recommendation grounded only in supplied facts and deterministic risks." }, { role: "user", content: JSON.stringify(context) }]); }
    catch { return this.fallback.generateHRRecommendation(context); }
  }
}
