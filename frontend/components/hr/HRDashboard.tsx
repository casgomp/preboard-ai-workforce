"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import type { EmployeeSnapshot } from "../../lib/types";
import { daysUntil, formatUpdated } from "../../lib/utils/date";
import { LoadingState } from "../shared/LoadingState";
import { StatusPill } from "../shared/StatusPill";
import { DocumentManager } from "../documents/DocumentManager";
import { KnowledgeGapPanel } from "./KnowledgeGapPanel";

const severityRank = { CRITICAL: 4, HIGH: 3, MEDIUM: 2, LOW: 1 };
const factLabels: Record<string, string> = { contract_status: "Contract", payroll_status: "Payroll", manager_assigned: "Manager assignment", employee_account: "Employee account", laptop_status: "Laptop", software_access: "Software permissions", badge_status: "Building badge", parking_status: "Parking", welcome_meeting: "Welcome meeting", day_one_agenda: "Day-one agenda", orientation_status: "Orientation" };
const categoryLabels: Record<string, string> = { HR: "HR", IT: "IT", FACILITIES: "Facilities", MANAGER: "Manager", ONBOARDING: "Learning / onboarding" };

function primaryRisk(snapshot: EmployeeSnapshot) { return [...snapshot.risks].sort((a, b) => severityRank[b.severity] - severityRank[a.severity])[0]; }

export function HRDashboard() {
  const [snapshots, setSnapshots] = useState<EmployeeSnapshot[] | null>(null);
  const [selected, setSelected] = useState("E001");
  const [busy, setBusy] = useState("");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  async function load() {
    try { const response = await fetch("/api/demo", { cache: "no-store" }); const payload = await response.json(); if (!response.ok) throw new Error(payload.error); setSnapshots(payload.data); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to load control center."); }
  }
  useEffect(() => { const timer = window.setTimeout(() => void load(), 0); return () => window.clearTimeout(timer); }, []);

  async function act(action: string) {
    setBusy(action); setNotice("");
    const response = await fetch("/api/demo", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ action }) });
    const payload = await response.json();
    if (!response.ok) setError(payload.error); else { await load(); setSelected("E001"); setNotice(action === "simulate-delay" ? "IT delay detected. Fact, score, risk and communication updated." : action === "resolve-laptop" ? "Temporary device assigned. Readiness recovered." : "Demo restored to its healthy starting state."); }
    setBusy("");
  }

  const summary = useMemo(() => {
    if (!snapshots) return null;
    const critical = snapshots.filter((item) => primaryRisk(item)?.severity === "CRITICAL").length;
    const atRisk = snapshots.filter((item) => ["HIGH", "MEDIUM"].includes(primaryRisk(item)?.severity ?? "")).length;
    return { starting: snapshots.length, critical, atRisk, ready: snapshots.length - critical - atRisk };
  }, [snapshots]);

  if (error && !snapshots) return <div className="mx-auto max-w-3xl px-6 py-24 text-center"><h1 className="text-2xl font-semibold">Control Center unavailable</h1><p className="mt-3 text-[#68736e]">{error}</p><button onClick={load} className="mt-6 rounded-full bg-[#173f35] px-5 py-2.5 text-sm text-white">Try again</button></div>;
  if (!snapshots || !summary) return <LoadingState label="Combining readiness signals…" />;
  const detail = snapshots.find((item) => item.employee.id === selected) ?? snapshots[0];
  const anna = snapshots.find((item) => item.employee.id === "E001")!;
  const annaLaptop = anna.facts.find((fact) => fact.key === "laptop_status")!;
  const annaRisk = primaryRisk(anna);
  const categories = ["HR", "IT", "FACILITIES", "MANAGER", "ONBOARDING"];

  return (
    <main className="min-h-screen bg-[#f2f4f3] pb-24 text-[#17231f]">
      <section className="mx-auto max-w-[1440px] px-5 pb-8 pt-9 lg:px-10 lg:pt-12">
        <div className="flex flex-col justify-between gap-6 lg:flex-row lg:items-end">
          <div><div className="mb-3 flex items-center gap-2"><span className="rounded-full bg-[#e4e9e6] px-3 py-1 text-[10px] font-semibold tracking-[.12em] text-[#53625c]">DEMO MODE</span><span className="text-xs text-[#7a8580]">Live operational picture</span></div><h1 className="text-4xl font-semibold tracking-[-0.05em] sm:text-5xl">Day One Readiness<br />Control Center</h1><p className="mt-4 max-w-2xl text-[#68736e]">See where the company is ready—and intervene before a new colleague feels the gap.</p></div>
          <div className="grid grid-cols-4 gap-2 rounded-2xl border border-black/5 bg-white p-2 shadow-sm">{[[summary.starting, "Starting soon"], [summary.ready, "Ready"], [summary.atRisk, "At risk"], [summary.critical, "Critical"]].map(([value, label]) => <div key={label} className="min-w-20 rounded-xl px-3 py-3 text-center sm:min-w-24"><p className="text-2xl font-semibold tracking-[-0.04em]">{value}</p><p className="mt-1 text-[10px] text-[#7a8580] sm:text-xs">{label}</p></div>)}</div>
        </div>

        <div className="mt-9 grid gap-6 xl:grid-cols-[1.3fr_.7fr]">
          <article className="overflow-hidden rounded-[26px] border border-black/5 bg-white shadow-sm">
            <div className="flex items-center justify-between border-b border-black/5 px-6 py-5"><div><h2 className="text-lg font-semibold">Employees starting soon</h2><p className="mt-1 text-xs text-[#7b8581]">Trusted current state · next 14 days</p></div><span className="rounded-full bg-[#f1f4f2] px-3 py-1 text-xs text-[#61706a]">{snapshots.length} people</span></div>
            <div className="overflow-x-auto"><table className="w-full min-w-[780px] border-collapse text-left text-sm"><thead className="bg-[#f8f9f8] text-[10px] uppercase tracking-[.11em] text-[#7a8580]"><tr>{["Employee", "Role", "Location", "Start", "Readiness", "Risk", "Primary blocker"].map((head) => <th key={head} className="px-5 py-3 font-semibold">{head}</th>)}</tr></thead><tbody>{snapshots.map((snapshot) => { const risk = primaryRisk(snapshot); return <tr key={snapshot.employee.id} onClick={() => setSelected(snapshot.employee.id)} className={`cursor-pointer border-t border-black/5 transition hover:bg-[#f8faf8] ${selected === snapshot.employee.id ? "bg-[#f0f5f2]" : ""}`}><td className="px-5 py-4"><Link href={`/hr/employees/${snapshot.employee.id}`} onClick={(event) => event.stopPropagation()} className="font-medium hover:underline">{snapshot.employee.name}</Link></td><td className="px-5 py-4 text-[#65706c]">{snapshot.employee.role}</td><td className="px-5 py-4 text-[#65706c]">{snapshot.employee.location}</td><td className="px-5 py-4">{daysUntil(snapshot.employee.startDate)}d</td><td className="px-5 py-4"><span className="font-semibold">{snapshot.readiness.score}%</span><span className="ml-2 inline-block h-1.5 w-10 overflow-hidden rounded-full bg-[#e6eae8]"><i className={`block h-full rounded-full ${snapshot.readiness.score < 80 ? "bg-[#c36345]" : "bg-[#4e9470]"}`} style={{ width: `${snapshot.readiness.score}%` }} /></span></td><td className="px-5 py-4">{risk ? <StatusPill value={risk.severity} friendly={`${risk.severity[0]}${risk.severity.slice(1).toLowerCase()} risk`} /> : <StatusPill value="READY" friendly="On track" />}</td><td className="px-5 py-4 text-[#65706c]">{risk && ["HIGH", "CRITICAL"].includes(risk.severity) ? `${factLabels[risk.factKey]} ${snapshot.facts.find((fact) => fact.key === risk.factKey)?.value.toLowerCase()}` : "—"}</td></tr>; })}</tbody></table></div>
          </article>

          <aside className="rounded-[26px] border border-[#d8d2c4] bg-[#ece7dc] p-6 shadow-sm"><div className="flex items-center justify-between"><div><p className="text-[10px] font-semibold tracking-[.14em] text-[#776f61]">PRESENTER TOOL</p><h2 className="mt-2 text-xl font-semibold">Demo controls</h2></div><span className="h-3 w-3 rounded-full bg-[#be7250] shadow-[0_0_0_5px_rgba(190,114,80,.12)]" /></div><p className="mt-3 text-sm leading-6 text-[#716b61]">Trigger the Fact → Risk → Action → Communication loop for Anna.</p><div className="mt-6 grid gap-2"><button disabled={!!busy || annaLaptop.value === "DELAYED"} onClick={() => act("simulate-delay")} className="rounded-xl bg-[#71442f] px-4 py-3 text-sm font-medium text-white transition hover:bg-[#603925] disabled:cursor-not-allowed disabled:opacity-40">{busy === "simulate-delay" ? "Updating…" : "Simulate IT Delay"}</button><button disabled={!!busy || annaLaptop.value !== "DELAYED"} onClick={() => act("resolve-laptop")} className="rounded-xl bg-[#173f35] px-4 py-3 text-sm font-medium text-white transition hover:bg-[#0e3028] disabled:cursor-not-allowed disabled:opacity-40">{busy === "resolve-laptop" ? "Resolving…" : "Resolve with temporary laptop"}</button><button disabled={!!busy} onClick={() => act("reset")} className="rounded-xl border border-black/10 bg-white/50 px-4 py-3 text-sm font-medium transition hover:bg-white disabled:opacity-40">Reset Demo</button></div>{notice && <p aria-live="polite" className="mt-4 rounded-xl bg-white/60 p-3 text-xs leading-5 text-[#4d5d56]">{notice}</p>}</aside>
        </div>

        {annaRisk && ["HIGH", "CRITICAL"].includes(annaRisk.severity) && <article className="mt-6 grid gap-5 rounded-[26px] border border-[#e7c6b7] bg-[#fff7f2] p-6 lg:grid-cols-[auto_1fr_auto] lg:items-center"><div className="grid h-12 w-12 place-items-center rounded-2xl bg-[#f7dfd3] text-lg font-semibold text-[#a45535]">!</div><div><div className="flex items-center gap-2"><StatusPill value={annaRisk.severity} /><span className="text-xs font-semibold uppercase tracking-[.11em] text-[#996047]">High priority</span></div><h2 className="mt-2 text-xl font-semibold">{annaRisk.title}</h2><p className="mt-1 text-sm text-[#6f625c]">Laptop preparation is delayed. Anna starts in {daysUntil(anna.employee.startDate)} days. <strong>Recommended action:</strong> {annaRisk.recommendedAction}.</p></div><div className="text-xs text-[#786a64]"><p>Source · {annaLaptop.sourceSystem}</p><p className="mt-1">Owner · {annaLaptop.ownerTeam}</p></div></article>}

        <div className="mt-6 grid gap-6 xl:grid-cols-[1.35fr_.65fr]">
          <article className="rounded-[26px] border border-black/5 bg-white p-6 shadow-sm"><div className="mb-6 flex items-start justify-between"><div><p className="text-[10px] font-semibold uppercase tracking-[.14em] text-[#7a8580]">Selected employee</p><h2 className="mt-2 text-2xl font-semibold">{detail.employee.name}</h2><p className="mt-1 text-sm text-[#6d7873]">{detail.employee.role} · {detail.employee.location} · starts in {daysUntil(detail.employee.startDate)} days</p></div><div className="text-right"><p className="text-3xl font-semibold tracking-[-0.05em]">{detail.readiness.score}%</p><Link href={`/hr/employees/${detail.employee.id}`} className="text-xs font-medium text-[#2e6b55] hover:underline">Open full profile →</Link></div></div><div className="grid gap-5 lg:grid-cols-2">{categories.map((category) => <section key={category} className="rounded-2xl border border-black/5 p-4"><h3 className="mb-3 text-xs font-semibold uppercase tracking-[.12em] text-[#65736d]">{categoryLabels[category]}</h3><div className="space-y-3">{detail.facts.filter((fact) => fact.category === category).map((fact) => <div key={fact.id} className="group flex items-start justify-between gap-3"><div><p className="text-sm font-medium">{factLabels[fact.key] ?? fact.key}</p><p className="mt-1 text-[11px] text-[#89918e]">{fact.ownerTeam} · {fact.sourceSystem}</p></div><StatusPill value={fact.value} /></div>)}</div></section>)}</div><details className="mt-5 rounded-2xl bg-[#f5f7f5] p-4"><summary className="cursor-pointer text-sm font-semibold">Why this score?</summary><div className="mt-4 overflow-x-auto"><table className="w-full min-w-[560px] text-left text-xs"><thead className="text-[#7c8782]"><tr><th className="pb-2">Requirement</th><th>Status</th><th>Weight</th><th>Contribution</th><th>Source</th></tr></thead><tbody>{detail.readiness.contributions.map((item) => <tr key={item.requirement.id} className="border-t border-black/5"><td className="py-2.5 font-medium">{item.requirement.name}</td><td>{item.fact?.value.replaceAll("_", " ") ?? "MISSING"}</td><td>{item.possible}</td><td>{item.earned.toFixed(1)} / {item.possible}</td><td>{item.fact?.sourceSystem ?? "—"}</td></tr>)}</tbody></table></div></details></article>

          <aside className="rounded-[26px] bg-[#172b26] p-6 text-white"><p className="text-[10px] font-semibold tracking-[.14em] text-white/45">FACT HISTORY</p><h2 className="mt-2 text-xl font-semibold">Latest changes</h2><div className="mt-6 space-y-1">{detail.history.slice(0, 6).map((event, index) => <div key={event.eventId} className="relative border-l border-white/10 pb-6 pl-5"><i className="absolute -left-1.5 top-1 h-3 w-3 rounded-full border-[3px] border-[#172b26] bg-[#87af9e]" /><div className="flex items-center justify-between gap-2"><p className="text-sm font-medium">{event.label ?? `${factLabels[event.factKey]} changed`}</p><time className="text-[10px] text-white/40">{formatUpdated(event.timestamp)}</time></div>{event.previousValue && <p className="mt-1 text-xs text-white/55">{event.previousValue} → {event.newValue}</p>}<p className="mt-1 text-[10px] text-white/35">Source: {event.sourceSystem}</p>{index === 0 && event.previousValue && <span className="mt-2 inline-block rounded bg-white/10 px-2 py-1 text-[9px]">LATEST</span>}</div>)}</div></aside>
        </div>
        <DocumentManager />
        <KnowledgeGapPanel />
      </section>
    </main>
  );
}
