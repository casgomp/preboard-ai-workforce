"use client";

// PLAN_PR14 D4: a visible marker whenever the demo clock is overridden, so nobody
// mistakes a scrubbed view for the real countdown, and nobody demos it by accident
// — it can only appear at all when the page was loaded with `?as_of=`.
import { useDemoClock } from "../../lib/demo-clock/DemoClockProvider";
import { formatDate } from "../../lib/utils/date";

export function DemoClockBanner() {
  const { today, isOverridden } = useDemoClock();
  if (!isOverridden) return null;
  return (
    <div className="bg-[#173f35] px-5 py-2 text-center text-xs font-medium text-[#b9d9c8]">
      Viewing as {formatDate(today.toISOString())} — demo clock, not the real date.
    </div>
  );
}
