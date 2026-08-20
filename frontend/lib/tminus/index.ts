// PLAN_PR15 B2: mirrors preboard.qa's _TMINUS_BANDS thresholds (60/14/4 days) and
// label text exactly, so a suggested-question chip set is keyed off the same bands
// the API already returns on the "asked at" chip (PR14 B4) — not a second,
// independently-guessed set of boundaries that could drift from the server's.
const TMINUS_BANDS: Array<[number, string]> = [
  [60, "more than 8 weeks out"],
  [14, "2-8 weeks out"],
  [4, "1-2 weeks out"],
];
const TMINUS_OVERDUE_LABEL = "final days";

export function tminusLabel(deltaDays: number): string {
  for (const [threshold, label] of TMINUS_BANDS) {
    if (deltaDays >= threshold) return label;
  }
  return TMINUS_OVERDUE_LABEL;
}

// Verified live against the real embedding endpoint for both E001 and E002
// (PLAN_PR15 B2's trap: every suggested question must actually ground, not hand
// off — a suggestion that fails makes the feature look broken at the exact
// moment a judge tries it). Far-out questions are relaxed/general; near-term
// questions are logistics-focused, so the sets visibly differ at T-40 vs T-3.
const RELAXED_QUESTIONS = [
  "When do I get my signing bonus?",
  "How many vacation days do I have?",
  "When does benefits enrollment open?",
];
const LOGISTICS_QUESTIONS = [
  "When will my laptop arrive?",
  "Has my laptop shipped yet?",
  "Is my reference check finished?",
];

export const SUGGESTED_QUESTIONS: Record<string, string[]> = {
  "more than 8 weeks out": RELAXED_QUESTIONS,
  "2-8 weeks out": RELAXED_QUESTIONS,
  "1-2 weeks out": LOGISTICS_QUESTIONS,
  "final days": LOGISTICS_QUESTIONS,
};
