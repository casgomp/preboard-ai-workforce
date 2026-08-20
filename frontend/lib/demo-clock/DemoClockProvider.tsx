"use client";

// PLAN_PR14 D1: one clock, in context, seeded from `?as_of=` on whatever page
// mounted it — rather than a URL param each component reads itself (candidate
// chat and the HR board could then disagree about what day it is, the one bug
// that would be visible on stage) or prop-drilling a date through five trees.
import { createContext, Suspense, useContext, useMemo, useState, type ReactNode } from "react";
import { useSearchParams } from "next/navigation";

type DemoClockValue = {
  today: Date;
  setToday: (date: Date) => void;
  // True whenever the page was loaded with `?as_of=`, regardless of whether the
  // scrubber has since been dragged back to today's real date (D4) — this gates
  // the scrubber's visibility and the "viewing as" banner, not a live comparison.
  isOverridden: boolean;
};

const DemoClockContext = createContext<DemoClockValue | null>(null);

function atLocalNoon(date: Date): Date {
  const normalized = new Date(date);
  normalized.setHours(12, 0, 0, 0);
  return normalized;
}

function parseAsOf(value: string | null): Date | null {
  if (!value) return null;
  const date = new Date(`${value}T12:00:00`);
  return Number.isNaN(date.getTime()) ? null : date;
}

function DemoClockProviderInner({ children }: { children: ReactNode }) {
  const searchParams = useSearchParams();
  const [initial] = useState(() => parseAsOf(searchParams.get("as_of")));
  const [isOverridden] = useState(initial !== null);
  const [today, setTodayState] = useState<Date>(() => initial ?? atLocalNoon(new Date()));

  const setToday = (date: Date) => setTodayState(atLocalNoon(date));

  const value = useMemo(() => ({ today, setToday, isOverridden }), [today, isOverridden]);
  return <DemoClockContext.Provider value={value}>{children}</DemoClockContext.Provider>;
}

// `useSearchParams()` needs a Suspense boundary around it; the fallback renders
// the real-clock default so the rest of the app isn't blocked on it.
export function DemoClockProvider({ children }: { children: ReactNode }) {
  return (
    <Suspense fallback={<DemoClockFallback>{children}</DemoClockFallback>}>
      <DemoClockProviderInner>{children}</DemoClockProviderInner>
    </Suspense>
  );
}

function DemoClockFallback({ children }: { children: ReactNode }) {
  const value = useMemo<DemoClockValue>(() => ({ today: atLocalNoon(new Date()), setToday: () => {}, isOverridden: false }), []);
  return <DemoClockContext.Provider value={value}>{children}</DemoClockContext.Provider>;
}

export function useDemoClock(): DemoClockValue {
  const context = useContext(DemoClockContext);
  if (!context) throw new Error("useDemoClock must be used within a DemoClockProvider");
  return context;
}
