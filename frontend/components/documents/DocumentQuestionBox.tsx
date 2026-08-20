"use client";

import { useState } from "react";
import type { GroundedAnswer } from "../../services/documents/types";
import { useDemoClock } from "../../lib/demo-clock/DemoClockProvider";
import { daysUntilStart, toISODate } from "../../lib/utils/date";
import { SUGGESTED_QUESTIONS, tminusLabel } from "../../lib/tminus";
import { DemoClockScrubber } from "./DemoClockScrubber";

// PLAN_PR15 B3/D6: client-side staged labels timed against typical latency, not a
// real trace of what the server is doing — recorded here, not narrated as
// instrumentation if a judge asks. Cleared in runAsk's `finally` so a slow call
// never leaves a stage showing after the response has already landed.
const STAGE_SEARCHING = "Searching your offer packet…";
const STAGE_WRITING = "Writing…";
const STAGE_STILL_WORKING = "Still working…";
const WRITING_DELAY_MS = 1200;
const FALLBACK_DELAY_MS = 6000;

export function DocumentQuestionBox({ variant = "dark", compact = false, startDate }: { variant?: "dark" | "light"; compact?: boolean; startDate?: string }) {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<GroundedAnswer | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [stage, setStage] = useState("");
  const [language, setLanguage] = useState<"en" | "de">("en");
  const dark = variant === "dark";
  const { today, isOverridden } = useDemoClock();

  async function runAsk(q: string) {
    if (!q.trim()) return;
    setBusy(true); setError(""); setResult(null); setStage(STAGE_SEARCHING);
    const writingTimer = window.setTimeout(() => setStage(STAGE_WRITING), WRITING_DELAY_MS);
    const fallbackTimer = window.setTimeout(() => setStage(STAGE_STILL_WORKING), FALLBACK_DELAY_MS);
    try {
      // PLAN_PR14 B1/B3: only send `as_of` while the demo clock is overridden — an
      // un-scrubbed candidate session behaves exactly as before that PR.
      // PLAN_PR15 D1/D2: only send `language` for the non-default toggle position —
      // English stays the no-instruction, pre-PR15 behavior.
      const body: Record<string, string> = { question: q, scope: "candidate" };
      if (isOverridden) body.as_of = toISODate(today);
      if (language === "de") body.language = language;
      const response = await fetch("/api/documents/ask", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      const payload = await response.json();
      if (!response.ok) setError(payload.error ?? "Unable to search company documents."); else setResult(payload);
    } finally {
      window.clearTimeout(writingTimer);
      window.clearTimeout(fallbackTimer);
      setBusy(false);
      setStage("");
    }
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

  function askSuggestion(q: string) {
    setQuestion(q);
    void runAsk(q);
  }

  // PLAN_PR15 B2: keyed off the same bands the "asked at" chip's threshold logic
  // uses (frontend/lib/tminus) — only shown before the first answer, on the empty
  // chat this feature exists for.
  const suggestions = !result && startDate ? SUGGESTED_QUESTIONS[tminusLabel(daysUntilStart(startDate, today))] : undefined;
  const dedupedCitations = result ? [...new Map(result.citations.map((citation) => [citation.documentId, citation])).values()] : [];

  return <div className={compact ? "" : "mt-6"}>
    {isOverridden && startDate && <DemoClockScrubber startDate={startDate} dark={dark} onRelease={onScrubberRelease} />}
    <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
      <div className="flex flex-wrap gap-2">
        {suggestions?.map((q) => <button key={q} type="button" disabled={busy} onClick={() => askSuggestion(q)} className={`rounded-full px-3 py-1.5 text-xs font-medium transition disabled:opacity-40 ${dark ? "bg-white/10 text-white/80 hover:bg-white/20" : "bg-[#eef3ef] text-[#35644f] hover:bg-[#e0ebe4]"}`}>{q}</button>)}
      </div>
      <div className={`ml-auto flex shrink-0 gap-0.5 rounded-full p-0.5 ${dark ? "bg-white/10" : "bg-[#eef1ef]"}`} role="group" aria-label="Answer language">
        <button type="button" onClick={() => setLanguage("en")} aria-pressed={language === "en"} className={`rounded-full px-2.5 py-1 text-[10px] font-semibold transition ${language === "en" ? "bg-white text-[#173f35]" : dark ? "text-white/50" : "text-[#7a8580]"}`}>EN</button>
        <button type="button" onClick={() => setLanguage("de")} aria-pressed={language === "de"} className={`rounded-full px-2.5 py-1 text-[10px] font-semibold transition ${language === "de" ? "bg-white text-[#173f35]" : dark ? "text-white/50" : "text-[#7a8580]"}`}>DE</button>
      </div>
    </div>
    <form onSubmit={ask} className={`flex gap-2 rounded-2xl p-2 ${dark ? "bg-white/10" : "border border-black/[.07] bg-[#f6f8f6]"}`}><label className="sr-only" htmlFor={`document-question-${variant}`}>Ask a question about company documents</label><input id={`document-question-${variant}`} value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Type any question…" className={`min-w-0 flex-1 bg-transparent px-3 py-2.5 text-sm outline-none ${dark ? "text-white placeholder:text-white/35" : "text-[#25332e] placeholder:text-[#87928d]"}`} /><button disabled={busy || !question.trim()} className={`shrink-0 rounded-xl px-5 py-2.5 text-sm font-semibold transition disabled:opacity-40 ${dark ? "bg-white text-[#173f35]" : "bg-[#173f35] text-white"}`}>{busy ? stage : "Ask"}</button></form>
    {error && <p role="alert" className={`mt-3 rounded-xl p-3 text-sm ${dark ? "bg-[#7a3f35]/35 text-[#ffd9cd]" : "bg-[#fff0e8] text-[#934e31]"}`}>{error}</p>}
    {result && <div aria-live="polite" className={`mt-4 rounded-2xl p-5 ${dark ? "bg-white text-[#25332e]" : "border border-black/[.06] bg-white"}`}>
      <div className="flex items-center gap-2"><span className={`h-2 w-2 rounded-full ${result.status === "SUPPORTED" ? "bg-[#4c9b73]" : "bg-[#c57a4f]"}`} /><p className="text-[10px] font-semibold uppercase tracking-[.13em] text-[#73807b]">{result.status === "SUPPORTED" ? "Grounded in company documents" : "No supported answer found"}</p>{result.askedAt && <span className="ml-auto rounded-full bg-[#eef3ef] px-2.5 py-1 text-[10px] font-medium text-[#35644f]">asked at {result.askedAt}</span>}</div>
      <p className="mt-3 text-sm leading-7">{result.answer}</p>
      {dedupedCitations.length > 0 && <div className="mt-4 border-t border-black/[.07] pt-3">
        <p className="text-[10px] font-semibold uppercase tracking-[.12em] text-[#86908c]">Sources</p>
        <div className="mt-2 space-y-1.5">{dedupedCitations.map((citation) => <details key={citation.documentId} className="group rounded-xl bg-[#f6f8f6] px-3 py-2"><summary className="flex cursor-pointer list-none items-center justify-between gap-3 text-xs font-medium text-[#35644f]"><span>{citation.title}</span><span className="shrink-0 text-[10px] font-normal text-[#8a938f] group-open:hidden">Show excerpt</span><span className="hidden shrink-0 text-[10px] font-normal text-[#8a938f] group-open:inline">Hide</span></summary><p className="mt-2 text-[11px] leading-5 text-[#5d6863]"><span className="mr-1 text-[9px] font-semibold uppercase tracking-wide text-[#8a938f]">Excerpt ·</span>{citation.excerpt}</p></details>)}</div>
      </div>}
      {result.handoff && <div className="mt-4 rounded-xl bg-[#fff2e9] p-3 text-sm text-[#744d3a]"><p className="font-semibold">Contact {result.handoff.department}</p><p className="mt-1 text-xs">{result.handoff.person} · <a className="underline" href={`mailto:${result.handoff.email}`}>{result.handoff.email}</a></p><p className="mt-2 text-[11px] text-[#8c6a56]">{result.handoff.department} usually replies within a day.</p></div>}
    </div>}
    <p className={`mt-3 text-[11px] ${dark ? "text-white/35" : "text-[#8a938f]"}`}>Answers are extractive and cited. If the documents cannot support an answer, you’ll be directed to the accountable team.</p>
  </div>;
}
