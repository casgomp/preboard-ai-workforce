import type { GroundedAnswer, SearchableChunk } from "./types";

const stopWords = new Set(["a", "about", "an", "and", "are", "can", "day", "do", "first", "for", "from", "how", "i", "in", "is", "it", "me", "my", "of", "on", "or", "should", "the", "to", "what", "when", "where", "which", "who", "will", "with"]);
const synonyms: Record<string, string[]> = { arrive: ["arrival", "lobby", "reception"], go: ["arrival", "lobby", "reception"], park: ["parking"], bring: ["photo", "identification"], wear: ["clothing", "attire", "casual"], computer: ["laptop", "device"], pay: ["payroll"] };
const contacts = [
  { department: "Workplace IT", person: "Michael Braun", email: "workplace-it@dayone.demo", terms: ["account", "computer", "device", "email", "it", "laptop", "login", "software", "technical"] },
  { department: "Facilities", person: "Laura Stein", email: "facilities@dayone.demo", terms: ["access", "badge", "building", "cafeteria", "desk", "food", "office", "park", "parking", "room", "transport"] },
  { department: "People Operations", person: "Julia Hartmann", email: "people-operations@dayone.demo", terms: ["benefit", "contract", "document", "holiday", "hr", "pay", "payroll", "policy", "salary", "tax"] },
  { department: "Learning & Onboarding", person: "Felix Weber", email: "onboarding@dayone.demo", terms: ["course", "learn", "orientation", "training"] },
];

export function tokenize(value: string) {
  const raw = value.toLowerCase().normalize("NFKD").replace(/[^a-z0-9\s-]/g, " ").split(/\s+/).filter((token) => (token.length > 2 || token === "go") && !stopWords.has(token));
  return [...new Set(raw.flatMap((token) => [token, ...(synonyms[token] ?? [])]))];
}

function wordMatches(words: Set<string>, token: string) { return words.has(token) || token.length >= 4 && [...words].some((word) => word.length >= 4 && (word.startsWith(token) || token.startsWith(word))); }

function scoreChunk(questionTokens: string[], chunk: SearchableChunk) {
  const words = new Set(`${chunk.title} ${chunk.department} ${chunk.content}`.toLowerCase().match(/[a-z0-9]+/g) ?? []);
  return questionTokens.reduce((score, token) => score + (wordMatches(words, token) ? 1 : 0), 0);
}

function bestSentences(content: string, questionTokens: string[]) {
  return content.split(/(?<=[.!?])\s+|\n+/).map((sentence) => sentence.trim()).filter((sentence) => sentence.length > 20).map((sentence) => { const words = new Set(sentence.toLowerCase().match(/[a-z0-9]+/g) ?? []); return { sentence, score: questionTokens.filter((token) => wordMatches(words, token)).length }; }).filter((item) => item.score > 0).sort((a, b) => b.score - a.score).slice(0, 3).map((item) => item.sentence);
}

export function routeQuestion(question: string) {
  const normalized = question.toLowerCase();
  return contacts.map((contact) => ({ ...contact, score: contact.terms.filter((term) => normalized.includes(term)).length })).sort((a, b) => b.score - a.score)[0];
}

export function answerFromChunks(question: string, chunks: SearchableChunk[]): GroundedAnswer {
  const questionTokens = tokenize(question);
  const minimumScore = questionTokens.length >= 3 ? 2 : 1;
  const ranked = chunks.map((chunk) => ({ chunk, score: scoreChunk(questionTokens, chunk) })).filter((item) => item.score >= minimumScore).sort((a, b) => b.score - a.score).slice(0, 3);
  const supported = ranked.flatMap(({ chunk }) => bestSentences(chunk.content, questionTokens).map((sentence) => ({ chunk, sentence })));
  if (questionTokens.length > 0 && supported.length > 0) {
    const uniqueSentences = [...new Set(supported.map((item) => item.sentence))].slice(0, 3);
    const citations = supported.filter((item, index, all) => all.findIndex((candidate) => candidate.chunk.documentId === item.chunk.documentId) === index).slice(0, 3).map(({ chunk, sentence }) => ({ documentId: chunk.documentId, title: chunk.title, excerpt: sentence }));
    return { status: "SUPPORTED", answer: uniqueSentences.join(" "), citations };
  }
  const handoff = routeQuestion(question);
  return { status: "NEEDS_HUMAN", answer: `I couldn’t find a supported answer in the available company documents. Please contact ${handoff.department} for a verified answer.`, citations: [], handoff: { department: handoff.department, person: handoff.person, email: handoff.email } };
}
