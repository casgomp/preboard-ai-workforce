import type { FactValue } from "../../lib/types";

const styles: Record<string, string> = {
  READY: "bg-[#e9f5ee] text-[#2e7054]", TEMPORARY_SOLUTION: "bg-[#eaf2f7] text-[#315d75]",
  IN_PROGRESS: "bg-[#f5f0e5] text-[#806a35]", DELAYED: "bg-[#fff0e7] text-[#9b4b23]",
  BLOCKED: "bg-[#fdeceb] text-[#a53a36]", MISSING: "bg-[#fdeceb] text-[#a53a36]",
  HIGH: "bg-[#fff0e7] text-[#9b4b23]", CRITICAL: "bg-[#fdeceb] text-[#a53a36]", MEDIUM: "bg-[#f5f0e5] text-[#806a35]", LOW: "bg-[#eef2f0] text-[#52635c]",
};

export function StatusPill({ value, friendly }: { value: FactValue | string; friendly?: string }) {
  return <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-semibold tracking-wide ${styles[value] ?? "bg-[#eef2f0] text-[#52635c]"}`}>{friendly ?? value.replaceAll("_", " ")}</span>;
}
