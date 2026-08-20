const DAY = 86_400_000;

export function dateInDays(days: number) {
  const date = new Date();
  date.setHours(12, 0, 0, 0);
  date.setDate(date.getDate() + days);
  return date.toISOString();
}

// PLAN_PR14 D3: signed, renamed from `daysUntil` so every call site gets looked at
// rather than silently inheriting negative behaviour — a past start date now reads
// as e.g. -3, not clamped to 0. `today` defaults to the real clock but takes an
// override so the demo clock (`useDemoClock`) can drive it.
export function daysUntilStart(iso: string, today: Date = new Date()) {
  const start = new Date(iso);
  const reference = new Date(today);
  start.setHours(12, 0, 0, 0);
  reference.setHours(12, 0, 0, 0);
  return Math.round((start.getTime() - reference.getTime()) / DAY);
}

// PLAN_PR14 D1: the demo clock stores `today` at local noon (matching the
// convention above and `dateInDays`), so slicing its UTC ISO string back to a
// calendar date round-trips correctly for realistic timezones.
export function toISODate(date: Date) {
  return date.toISOString().slice(0, 10);
}

export function formatDate(iso: string) {
  return new Intl.DateTimeFormat("en-GB", { weekday: "long", day: "numeric", month: "long" }).format(new Date(iso));
}

export function formatUpdated(iso: string) {
  return new Intl.DateTimeFormat("en-GB", { hour: "2-digit", minute: "2-digit" }).format(new Date(iso));
}
