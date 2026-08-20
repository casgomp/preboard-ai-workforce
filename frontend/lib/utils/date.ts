const DAY = 86_400_000;

export function dateInDays(days: number) {
  const date = new Date();
  date.setHours(12, 0, 0, 0);
  date.setDate(date.getDate() + days);
  return date.toISOString();
}

export function daysUntil(iso: string) {
  const start = new Date(iso);
  const today = new Date();
  start.setHours(12, 0, 0, 0);
  today.setHours(12, 0, 0, 0);
  return Math.max(0, Math.round((start.getTime() - today.getTime()) / DAY));
}

export function formatDate(iso: string) {
  return new Intl.DateTimeFormat("en-GB", { weekday: "long", day: "numeric", month: "long" }).format(new Date(iso));
}

export function formatUpdated(iso: string) {
  return new Intl.DateTimeFormat("en-GB", { hour: "2-digit", minute: "2-digit" }).format(new Date(iso));
}
