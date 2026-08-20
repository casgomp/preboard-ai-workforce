"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { EmployeeSnapshot, FactValue } from "../../lib/types";
import { daysUntilStart, formatDate, formatRelativeDay } from "../../lib/utils/date";
import { LoadingState } from "../shared/LoadingState";
import { DocumentQuestionBox } from "../documents/DocumentQuestionBox";
import { useDemoClock } from "../../lib/demo-clock/DemoClockProvider";
import { DemoClockBanner } from "../shared/DemoClockBanner";

const overview = [
  ["Employment details", ["contract_status", "payroll_status"]],
  ["Account & access", ["employee_account", "software_access"]],
  ["Equipment", ["laptop_status"]], ["Workplace access", ["badge_status", "parking_status"]],
  ["Manager & team", ["manager_assigned", "welcome_meeting"]], ["First-day schedule", ["day_one_agenda"]],
  ["Orientation", ["orientation_status"]],
] as const;

const schedule = [
  ["08:45", "Arrive at Wolfsburg Office", "North lobby"], ["09:00", "Meet your manager", "Welcome lounge"],
  ["09:30", "Laptop and account setup", "Workplace IT"], ["10:30", "Meet the team", "Digital Engineering"],
  ["12:00", "Lunch with the team", "Campus restaurant"], ["14:00", "New employee orientation", "Learning studio"],
  ["16:00", "First-day wrap-up", "With your manager"],
];

// PLAN_PR15 B7: daysUntilStart is signed since PR14 — a past start date must not
// render as a bare minus sign on the one number meant to be readable across a room.
function countdownHero(days: number): { big: string; label: string } {
  if (days > 0) return { big: String(days), label: days === 1 ? "day until your first day" : "days until your first day" };
  if (days === 0) return { big: "Today", label: "is your first day" };
  const since = -days;
  return { big: String(since), label: since === 1 ? "day since you started" : "days since you started" };
}

function friendlyStatus(values: FactValue[]) {
  if (values.includes("MISSING") || values.includes("BLOCKED")) return "Action needed";
  if (values.includes("DELAYED")) return "We’re handling it";
  if (values.includes("IN_PROGRESS")) return "In progress";
  return "Ready";
}

export function CandidateDashboard({ employeeId }: { employeeId: string }) {
  const [snapshot, setSnapshot] = useState<EmployeeSnapshot | null>(null);
  const [error, setError] = useState("");
  const { today } = useDemoClock();

  const load = useCallback(async () => {
    try {
      const response = await fetch(`/api/demo?employeeId=${employeeId}&view=candidate`, { cache: "no-store" });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error);
      setSnapshot(payload.data);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to load readiness."); }
  }, [employeeId]);
  useEffect(() => { const timer = window.setTimeout(() => void load(), 0); return () => window.clearTimeout(timer); }, [load]);

  const preparation = useMemo(() => snapshot ? overview.map(([label, keys]) => ({ label, status: friendlyStatus(snapshot.facts.filter((fact) => (keys as readonly string[]).includes(fact.key)).map((fact) => fact.value)) })) : [], [snapshot]);
  if (error) return <div className="mx-auto max-w-3xl px-6 py-24 text-center"><h1 className="text-2xl font-semibold">We couldn’t load your Day One view.</h1><p className="mt-3 text-[#68736e]">{error}</p><button onClick={load} className="mt-6 rounded-full bg-[#173f35] px-5 py-2.5 text-sm text-white">Try again</button></div>;
  if (!snapshot) return <LoadingState />;

  const { employee, readiness, candidateUpdate } = snapshot;
  const delayed = snapshot.facts.some((fact) => fact.value === "DELAYED");
  const temporary = snapshot.facts.some((fact) => fact.value === "TEMPORARY_SOLUTION");
  const headline = delayed ? "We’re handling a final detail" : temporary ? "Your essentials are ready" : "Everything is on track";
  const ringDegrees = Math.round(readiness.score * 3.6);
  const hero = countdownHero(daysUntilStart(employee.startDate, today));
  const recentChanges = [...snapshot.history].sort((a, b) => b.timestamp.localeCompare(a.timestamp)).slice(0, 5);

  return (
    <main className="bg-[#f5f6f2] pb-24 text-[#17231f]">
      <DemoClockBanner />
      <section className="mx-auto max-w-7xl px-5 pb-12 pt-10 lg:px-10 lg:pt-16">
        <div className="mb-9 flex flex-col justify-between gap-6 lg:flex-row lg:items-end">
          <div><p className="mb-3 text-xs font-semibold uppercase tracking-[0.2em] text-[#73807b]">Your Day One</p><h1 className="text-4xl font-semibold tracking-[-0.05em] sm:text-6xl">Welcome, {employee.name.split(" ")[0]}.</h1><p className="mt-4 max-w-2xl text-lg leading-8 text-[#5e6965]">Everything you need for a confident start, brought together in one calm, clear place.</p></div>
          <div className="rounded-[28px] border border-black/5 bg-white px-8 py-6 text-center shadow-sm"><p className="text-8xl font-semibold leading-none tracking-[-0.06em] tabular-nums sm:text-9xl">{hero.big}</p><p className="mt-3 text-base text-[#6b7571]">{hero.label}</p></div>
        </div>

        <div className="grid gap-6 lg:grid-cols-[1.15fr_.85fr]">
          <article className={`overflow-hidden rounded-[30px] p-7 text-white shadow-[0_22px_60px_rgba(23,63,53,.18)] sm:p-10 ${delayed ? "bg-[#6f4c32]" : "bg-[#173f35]"}`}>
            <div className="flex flex-col justify-between gap-10 sm:flex-row">
              <div><p className="text-xs font-semibold tracking-[.14em] text-white/60">DAY ONE READINESS</p><p className="mt-5 text-7xl font-semibold tracking-[-0.07em]">{readiness.score}<span className="text-4xl text-[#b9d9c8]">%</span></p><h2 className="mt-5 text-2xl font-medium">{headline}</h2><p className="mt-2 max-w-md leading-7 text-white/65">{candidateUpdate}</p></div>
              <div className="mx-auto grid h-36 w-36 shrink-0 place-items-center rounded-full sm:mx-0" style={{ background: `conic-gradient(#b9d9c8 0deg ${ringDegrees}deg, rgba(255,255,255,.14) ${ringDegrees}deg)` }}><div className={`grid h-28 w-28 place-items-center rounded-full text-sm font-medium text-white/80 ${delayed ? "bg-[#6f4c32]" : "bg-[#173f35]"}`}>{delayed ? "In hand" : "On track"}</div></div>
            </div>
            <div className="mt-10 h-1.5 overflow-hidden rounded-full bg-white/10"><div className="h-full rounded-full bg-[#b9d9c8] transition-[width] duration-700" style={{ width: `${readiness.score}%` }} /></div>
          </article>

          <article className="rounded-[30px] border border-black/5 bg-white p-7 shadow-sm sm:p-8">
            <div className="flex items-center justify-between"><div><p className="text-xs font-semibold tracking-[.14em] text-[#74807b]">STARTING</p><h2 className="mt-2 text-xl font-semibold">{formatDate(employee.startDate)}</h2></div><span className="rounded-full bg-[#eef4ef] px-3 py-1.5 text-xs font-semibold text-[#2e6b55]">{employee.location.toUpperCase()}</span></div>
            <div className="mt-8 grid grid-cols-2 gap-6 border-t border-black/5 pt-6 text-sm"><div><p className="text-[#8a938f]">Role</p><p className="mt-1 font-medium">{employee.role}</p></div><div><p className="text-[#8a938f]">Department</p><p className="mt-1 font-medium">{employee.department}</p></div><div><p className="text-[#8a938f]">Manager</p><p className="mt-1 font-medium">{employee.managerName}</p></div><div><p className="text-[#8a938f]">Arrival</p><p className="mt-1 font-medium">08:45 · North lobby</p></div></div>
          </article>
        </div>

        <div className="mt-6 grid gap-6 lg:grid-cols-[.82fr_1.18fr]">
          <article className="rounded-[30px] border border-black/5 bg-white p-7 shadow-sm sm:p-8"><div className="mb-6 flex items-center justify-between"><h2 className="text-xl font-semibold tracking-[-0.025em]">Preparation overview</h2><span className="text-[10px] font-semibold tracking-[.12em] text-[#7a8580]">LIVE STATUS</span></div><div className="divide-y divide-black/5">{preparation.map(({ label, status }) => <div key={label} className="flex items-center justify-between py-3.5 text-sm"><span>{label}</span><span className={`flex items-center gap-2 font-medium ${status === "Ready" ? "text-[#2f7459]" : status === "In progress" ? "text-[#8a6b2b]" : "text-[#99613b]"}`}><i className="h-2 w-2 rounded-full bg-current" />{status}</span></div>)}</div></article>
          <article className="rounded-[30px] border border-black/5 bg-[#ede7dc] p-7 sm:p-8"><p className="text-xs font-semibold tracking-[.14em] text-[#70695d]">YOUR FIRST-DAY DIGITAL TWIN</p><h2 className="mt-2 text-2xl font-semibold tracking-[-0.03em]">Your first day, already taking shape.</h2><div className="mt-8 grid gap-x-8 sm:grid-cols-2">{schedule.map(([time, item, place], index) => <div key={time} className="relative flex gap-4 border-l border-[#173f35]/15 pb-6 pl-5"><span className="absolute -left-1.5 top-1 h-3 w-3 rounded-full border-[3px] border-[#ede7dc] bg-[#3b735f]" /><div className="w-12 shrink-0 text-xs font-semibold text-[#61716a]">{time}</div><div><p className="text-sm font-medium">{item}</p><p className="mt-1 text-xs text-[#837e74]">{place} · 0{index + 1}</p></div></div>)}</div></article>
        </div>

        {recentChanges.length > 0 && <article className="mt-6 rounded-[30px] border border-black/5 bg-white p-7 shadow-sm sm:p-8">
          <div className="mb-6 flex items-center justify-between"><h2 className="text-xl font-semibold tracking-[-0.025em]">Recent updates</h2><span className="text-[10px] font-semibold tracking-[.12em] text-[#7a8580]">SINCE YOU SIGNED</span></div>
          <div className="divide-y divide-black/5">{recentChanges.map((event) => <div key={event.eventId} className="flex items-center justify-between gap-4 py-3.5 text-sm"><span className="text-[#25332e]">{event.label ?? `${event.factKey} updated`}</span><time className="shrink-0 text-xs text-[#8a938f]">{formatRelativeDay(event.timestamp)}</time></div>)}</div>
        </article>}

        <article className="mt-6 rounded-[30px] bg-[#132a25] p-7 text-white sm:p-10"><div className="grid gap-9 lg:grid-cols-[.75fr_1.25fr]"><div><p className="text-xs font-semibold tracking-[.14em] text-white/50">COMPANY KNOWLEDGE</p><h2 className="mt-3 text-3xl font-semibold tracking-[-0.04em]">Ask anything about your first day.</h2><p className="mt-3 leading-7 text-white/60">Every answer must be supported by an employee-safe company document. No document evidence means no invented answer.</p></div><DocumentQuestionBox variant="dark" compact startDate={employee.startDate} /></div></article>
      </section>
    </main>
  );
}
