"use client";

// PLAN_PR14 B3/D4: only ever mounted while `?as_of=` is present (the parent gates
// it), range from the start date back MAX_DAYS_BEFORE_START days — a stand-in for
// "the signing date" since Employee has no tracked signing date, chosen to clear
// every _TMINUS_BANDS threshold in preboard/qa.py (60/14/4 days) with headroom.
import { useState } from "react";
import { useDemoClock } from "../../lib/demo-clock/DemoClockProvider";

const DAY_MS = 86_400_000;
const MAX_DAYS_BEFORE_START = 90;

function atNoon(date: Date): Date {
  const normalized = new Date(date);
  normalized.setHours(12, 0, 0, 0);
  return normalized;
}

function daysBeforeStart(startDate: string, today: Date): number {
  const start = atNoon(new Date(startDate));
  const ref = atNoon(today);
  const diff = Math.round((start.getTime() - ref.getTime()) / DAY_MS);
  return Math.min(MAX_DAYS_BEFORE_START, Math.max(0, diff));
}

function dateFromDaysBeforeStart(startDate: string, days: number): Date {
  const start = atNoon(new Date(startDate));
  return new Date(start.getTime() - days * DAY_MS);
}

export function DemoClockScrubber({ startDate, dark, onRelease }: { startDate: string; dark: boolean; onRelease: () => void }) {
  const { today, setToday } = useDemoClock();
  const [dragging, setDragging] = useState(false);
  const value = daysBeforeStart(startDate, today);

  function handleChange(event: React.ChangeEvent<HTMLInputElement>) {
    setDragging(true);
    setToday(dateFromDaysBeforeStart(startDate, Number(event.target.value)));
  }

  // Range inputs fire React's onChange continuously while dragging (that's what
  // drives the live countdown), but the re-ask (B3's "releasing it re-posts the
  // last question") should fire once, on release — plain DOM mouseup/touchend/keyup
  // rather than a second onChange, since React has no separate "drag ended" event.
  function handleRelease() {
    if (!dragging) return;
    setDragging(false);
    onRelease();
  }

  return (
    <div className={`mb-3 rounded-xl px-3 py-2.5 text-xs ${dark ? "bg-white/10" : "border border-black/[.07] bg-[#f6f8f6]"}`}>
      <div className={`flex items-center justify-between text-[11px] font-medium ${dark ? "text-white/70" : "text-[#556059]"}`}>
        <span>Demo clock</span>
        <span>{value === 0 ? "Start date" : `T−${value} days`}</span>
      </div>
      <input
        type="range"
        min={0}
        max={MAX_DAYS_BEFORE_START}
        value={value}
        onChange={handleChange}
        onMouseUp={handleRelease}
        onTouchEnd={handleRelease}
        onKeyUp={handleRelease}
        aria-label="Demo clock: days before start date"
        className={`mt-2 w-full ${dark ? "accent-white" : "accent-[#173f35]"}`}
      />
    </div>
  );
}
