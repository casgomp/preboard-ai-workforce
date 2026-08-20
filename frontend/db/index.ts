import { env } from "cloudflare:workers";

export function getDocumentBindings() {
  if (!env.DB || !env.DOCS) throw new Error("Local document storage is unavailable. Start the app with npm run dev so the DB and DOCS bindings are created.");
  return { db: env.DB, bucket: env.DOCS };
}
