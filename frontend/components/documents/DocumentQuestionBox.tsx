"use client";

import { useState } from "react";
import type { GroundedAnswer } from "../../services/documents/types";
import { useDemoClock } from "../../lib/demo-clock/DemoClockProvider";
import { toISODate } from "../../lib/utils/date";
import { DemoClockScrubber } from "./DemoClockScrubber";

export function DocumentQuestionBox({ variant = "dark", compact = false, startDate }: { variant?: "dark" | "light"; compact?: boolean; startDate?: string }) {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<GroundedAnswer | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const dark = variant === "dark";
  const { today, isOverridden } = useDemoClock();

  async function runAsk(q: string) {
    if (!q.trim()) return;
    setBusy(true); setError(""); setResult(null);
    // PLAN_PR14 B1/B3: only send `as_of` while the demo clock is overridden — an
    // un-scrubbed candidate session behaves exactly as before this PR.
    const body = isOverridden ? { question: q, scope: "candidate", as_of: toISODate(today) } : { question: q, scope: "candidate" };
    const response = await fetch("/api/documents/ask", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const payload = await response.json();
    if (!response.ok) setError(payload.error ?? "Unable to search company documents."); else setResult(payload);
    setBusy(false);
  }

  async function ask(event: React.FormEvent) {
    event.preventDefault();
    await runAsk(question);
  }

  // PLAN_PR14 B3: releasing the scrubber re-posts the last question at the new
  // clock position, replacing the previous answer (setResult inside runAsk
  // overwrites) rather than appending an unlabelled duplicate.
  function onScrubberRelease() {
    if (result && question.trim()) void runAsk(question);
  }

  return <div className={compact ? "" : "mt-6"}>{isOverridden && startDate && <DemoClockScrubber startDate={startDate} dark={dark} onRelease={onScrubberRelease} />}<form onSubmit={ask} className={`flex gap-2 rounded-2xl p-2 ${dark ? "bg-white/10" : "border border-black/[.07] bg-[#f6f8f6]"}`}><label className="sr-only" htmlFor={`document-question-${variant}`}>Ask a question about company documents</label><input id={`document-question-${variant}`} value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Type any question…" className={`min-w-0 flex-1 bg-transparent px-3 py-2.5 text-sm outline-none ${dark ? "text-white placeholder:text-white/35" : "text-[#25332e] placeholder:text-[#87928d]"}`} /><button disabled={busy || !question.trim()} className={`shrink-0 rounded-xl px-5 py-2.5 text-sm font-semibold transition disabled:opacity-40 ${dark ? "bg-white text-[#173f35]" : "bg-[#173f35] text-white"}`}>{busy ? "Searching…" : "Ask"}</button></form>{error && <p role="alert" className={`mt-3 rounded-xl p-3 text-sm ${dark ? "bg-[#7a3f35]/35 text-[#ffd9cd]" : "bg-[#fff0e8] text-[#934e31]"}`}>{error}</p>}{result && <div aria-live="polite" className={`mt-4 rounded-2xl p-5 ${dark ? "bg-white text-[#25332e]" : "border border-black/[.06] bg-white"}`}><div className="flex items-center gap-2"><span className={`h-2 w-2 rounded-full ${result.status === "SUPPORTED" ? "bg-[#4c9b73]" : "bg-[#c57a4f]"}`} /><p className="text-[10px] font-semibold uppercase tracking-[.13em] text-[#73807b]">{result.status === "SUPPORTED" ? "Grounded in company documents" : "No supported answer found"}</p>{result.askedAt && <span className={`ml-auto rounded-full px-2.5 py-1 text-[10px] font-medium ${dark ? "bg-[#edf3ef] text-[#35644f]" : "bg-[#eef3ef] text-[#35644f]"}`}>asked at {result.askedAt}</span>}</div><p className="mt-3 text-sm leading-7">{result.answer}</p>{result.citations.length > 0 && <div className="mt-4 border-t border-black/[.07] pt-3"><p className="text-[10px] font-semibold uppercase tracking-[.12em] text-[#86908c]">Sources</p><div className="mt-2 flex flex-wrap gap-2">{[...new Map(result.citations.map((citation) => [citation.documentId, citation])).values()].map((citation) => <span key={citation.documentId} title={citation.excerpt} className="rounded-full bg-[#edf3ef] px-3 py-1.5 text-xs font-medium text-[#35644f]">{citation.title}</span>)}</div></div>}{result.handoff && <div className="mt-4 rounded-xl bg-[#fff2e9] p-3 text-sm text-[#744d3a]"><p className="font-semibold">Contact {result.handoff.department}</p><p className="mt-1 text-xs">{result.handoff.person} · <a className="underline" href={`mailto:${result.handoff.email}`}>{result.handoff.email}</a></p></div>}</div>}<p className={`mt-3 text-[11px] ${dark ? "text-white/35" : "text-[#8a938f]"}`}>Answers are extractive and cited. If the documents cannot support an answer, you’ll be directed to the accountable team.</p></div>;
}
