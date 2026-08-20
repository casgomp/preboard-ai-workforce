"use client";

import { useEffect, useState } from "react";

type DepartmentGap = { department: string; count: number; distinctQuestions: number; distinctOffers: number; lastSeen: string };
type QuestionGap = { question: string; department: string | null; count: number; distinctOffers: number; lastSeen: string };
// PLAN_PR14 B5: chronologically ordered by the server (preboard.gap_report.countdown_gap_report), not by count.
type CountdownGap = { bucket: string; count: number; distinctQuestions: number; distinctOffers: number; lastSeen: string };

// PLAN_PR15 B6/D5: one row, one click, one call — never fired automatically on
// page load (that would be an FM call per row on every load, producing unreviewed
// text that looks like policy before anyone asked for it).
function GapQuestionRow({ item }: { item: QuestionGap }) {
  const [state, setState] = useState<{ status: "idle" | "busy" | "done" | "error"; draft?: string; error?: string }>({ status: "idle" });
  const owner = item.department ?? "the accountable team";

  async function onDraft() {
    setState({ status: "busy" });
    try {
      const response = await fetch("/api/draft-section", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question: item.question, department: owner }) });
      const payload = await response.json();
      if (!response.ok) setState({ status: "error", error: payload.error ?? "Unable to draft a section." });
      else setState({ status: "done", draft: payload.draft });
    } catch {
      setState({ status: "error", error: "Unable to reach the document assistant." });
    }
  }

  return <>
    <tr className="border-t border-black/[.05]">
      <td className="px-4 py-3 font-medium">{item.question}</td>
      <td className="px-4 py-3 text-[#6f7b76]">{owner}</td>
      <td className="px-4 py-3 text-right font-semibold">{item.count}</td>
      <td className="px-4 py-3 text-right">
        <button onClick={onDraft} disabled={state.status === "busy"} className="rounded-full border border-black/10 px-3 py-1 text-[11px] font-medium text-[#53645d] transition hover:bg-[#f5f7f5] disabled:opacity-40">
          {state.status === "busy" ? "Drafting…" : state.status === "done" ? "Redraft" : "Draft"}
        </button>
      </td>
    </tr>
    {state.status === "done" && <tr className="border-t border-black/[.05] bg-[#f7f8f7]">
      <td colSpan={4} className="px-4 py-3">
        <p className="mb-1.5 text-[9px] font-semibold uppercase tracking-wide text-[#8a938f]">Draft — needs review by {owner}</p>
        <p className="text-xs leading-5 text-[#3f4a45]">{state.draft}</p>
      </td>
    </tr>}
    {state.status === "error" && <tr className="border-t border-black/[.05]"><td colSpan={4} className="px-4 py-3 text-xs text-[#914b2d]">{state.error}</td></tr>}
  </>;
}

export function KnowledgeGapPanel() {
  const [data, setData] = useState<{ departments: DepartmentGap[]; questions: QuestionGap[]; countdown: CountdownGap[] } | null>(null);
  const [error, setError] = useState("");

  async function load() {
    setError("");
    const response = await fetch("/api/knowledge-gaps", { cache: "no-store" });
    const payload = await response.json();
    if (response.ok) setData(payload); else setError(payload.error ?? "Unable to load knowledge gaps.");
  }

  useEffect(() => { const timer = window.setTimeout(() => void load(), 0); return () => window.clearTimeout(timer); }, []);

  return <section className="mt-6 rounded-[28px] border border-black/[.06] bg-white p-6 shadow-sm lg:p-8"><div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end"><div><p className="text-[10px] font-semibold uppercase tracking-[.14em] text-[#65736d]">Learning loop</p><h2 className="mt-2 text-2xl font-semibold tracking-[-0.035em]">Knowledge gaps</h2><p className="mt-2 text-sm text-[#6d7873]">Questions the document library could not support, routed to the accountable team.</p></div><button onClick={load} className="self-start rounded-full border border-black/10 px-4 py-2 text-xs font-medium text-[#53645d] hover:bg-[#f5f7f5]">Refresh</button></div>{error && <p role="alert" className="mt-5 rounded-xl bg-[#fff0e8] p-3 text-sm text-[#914b2d]">{error}</p>}{data && data.questions.length === 0 && <div className="mt-6 rounded-2xl bg-[#f5f7f5] p-6 text-sm text-[#71807a]">No unsupported questions have been logged yet.</div>}{data && data.questions.length > 0 && <div className="mt-6 grid gap-6 xl:grid-cols-[.7fr_1.3fr]"><div><h3 className="text-sm font-semibold">By department</h3><div className="mt-3 space-y-2">{data.departments.map((item) => <div key={item.department} className="rounded-xl bg-[#f5f7f5] p-4"><div className="flex items-center justify-between"><p className="text-sm font-medium">{item.department}</p><span className="rounded-full bg-white px-2.5 py-1 text-xs font-semibold">{item.count}</span></div><p className="mt-1 text-[11px] text-[#7c8782]">{item.distinctQuestions} distinct question{item.distinctQuestions === 1 ? "" : "s"} · {item.distinctOffers} user{item.distinctOffers === 1 ? "" : "s"}</p></div>)}</div></div><div><h3 className="text-sm font-semibold">Most common unanswered questions</h3><div className="mt-3 overflow-hidden rounded-xl border border-black/[.06]"><table className="w-full text-left text-xs"><thead className="bg-[#f7f8f7] text-[10px] uppercase tracking-[.1em] text-[#7b8681]"><tr><th className="px-4 py-3">Question</th><th className="px-4 py-3">Owner</th><th className="px-4 py-3 text-right">Count</th><th className="px-4 py-3 text-right">Draft</th></tr></thead><tbody>{data.questions.map((item) => <GapQuestionRow key={`${item.question}-${item.department}`} item={item} />)}</tbody></table></div></div></div>}{data && data.countdown.length > 0 && <div className="mt-6"><h3 className="text-sm font-semibold">By countdown position</h3><p className="mt-1 text-[11px] text-[#7c8782]">Not just what candidates ask — when. Ordered from farthest out to closest.</p><div className="mt-3 space-y-2">{data.countdown.map((item) => <div key={item.bucket} className="flex items-center gap-3"><span className="w-44 shrink-0 text-xs text-[#556059]">{item.bucket}</span><div className="h-5 flex-1 overflow-hidden rounded-full bg-[#f0f3f1]"><div className="h-full rounded-full bg-[#4e9470]" style={{ width: `${Math.max(6, (item.count / Math.max(...data.countdown.map((c) => c.count))) * 100)}%` }} /></div><span className="w-8 shrink-0 text-right text-xs font-semibold">{item.count}</span></div>)}</div></div>}</section>;
}
