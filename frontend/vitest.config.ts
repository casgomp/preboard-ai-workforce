import { defineConfig } from "vitest/config";

// AUTH_SECRET (PR12/NOTES.md §19, D3/R4): session.ts now throws instead of falling
// back to a committed dev secret, so tests need their own value to sign/verify with.
export default defineConfig({
  test: { environment: "node", include: ["tests/**/*.test.ts"], env: { AUTH_SECRET: "test-only-secret" } },
});
