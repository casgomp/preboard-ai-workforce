# NOTES – preboard

Preboarding Q&A buffer for signed-but-not-started hires. Answers questions from the
offer packet and preboarding docs, hands off to HR when it can't, logs what it missed.

Stack: Python, Databricks Free Edition (serverless-only). Retrieval corpus in Unity
Catalog, generation via a Foundation Model endpoint, chat UI as a Databricks App, miss
log as a SQL table. App framework undecided – see PR1.

Team of 4, 48-hour hackathon build. Claude writes implementation directly this project
(no local pairing/scaffolding needed) – speed over teaching.

## §1 Durable invariants

1. The bot's only actions are answer, hand off, and log. It never rejects, ranks, or
   writes to an HR system.
2. Pre day-1 makes no anonymity claim. The answerer is HR and already knows the
   candidate by name. The value is volume absorption, not unlinkability. Any token-split
   or k-anonymity work belongs to the day-1 variant, not here.
3. No answer without a retrieved chunk. Every answer is grounded in retrieved doc
   content and names its source document.
4. Low retrieval confidence hands off to a named human. The bot never guesses past its
   corpus.
5. Auth is per-offer and scoped to one candidate. No internal directory identity exists
   at this phase.

## §2 Active deferred work

- **Day-1 anonymity variant** – token-split identity store, k-thresholded peer-facing
  buffer, colleague-facing questions. TRIGGER: the candidate gains internal identity and
  colleagues, i.e. first login on or after the start date.
- **Gap report** – miss log ranked by frequency, aggregated across all past candidates
  rather than the current cohort (a signed cohort is often one to three people, so a
  per-cohort count is near-empty and non-anonymous). TRIGGER: the answer → handoff → log
  loop is demoable end to end.
- **German-first corpus** – FM endpoint handles the language; the corpus and citations
  must match. TRIGGER: the demo audience needs German, or the source docs are German.
- **Keyword-overlap retrieval gives false positives on common words** – e.g. "your" and
  incidental proper nouns/dates that recur across sections inflate overlap scores
  regardless of topic (hit twice while writing PR1a's tests, both fixed by widening the
  stopword list, not by a structural fix). Real vector search should not have this
  failure mode, but until PR1b lands, widen `_STOPWORDS` in `retrieval.py` when it
  recurs rather than trusting the threshold blindly. TRIGGER: PR1b (real retrieval).

## §3 Shipped

- **PR1a** (2026-08-20, `63145d3`) – vertical slice proving ask → grounded answer with
  citation → low-confidence handoff → miss logged, entirely local (keyword-overlap
  retrieval, stub generator, SQLite miss log, CLI front end). No Databricks connection
  required to run or test it. See NOTES_ARCHIVE.md for the design record.

## §4 Release order

1. PR1a – thinnest vertical slice: one hardcoded offer/candidate, keyword-overlap
   retrieval over one local offer packet (no vector search yet), stub or real FM
   generation behind a swappable interface, fixed confidence threshold, miss log in
   local SQLite (same shape as the eventual UC table), CLI front end (Databricks App
   deferred out of the critical path). Proves ask → grounded answer with citation →
   low-confidence handoff → miss logged end to end without any Databricks credentials.
2. PR1b – real per-offer auth (stateless signed magic-link tokens) and a second
   candidate in the corpus, so auth scoping is actually demonstrable.
3. PR1c – swap in Unity Catalog + vector search retrieval and the Databricks App UI.
4. PR2 – gap report.

First slice cut line: if the loop in PR1a isn't demoable by end of day 1, PR1b's real
retrieval/auth and PR2 are both dropped from the pitch and named as future work instead.

## §5 PR1a decisions

- **Confidence scoring**: token-overlap ratio between question and chunk (no
  embeddings yet). Threshold is a named constant in `retrieval.py`, tuned against the
  sample corpus, and explicitly called out as needing revisit once real vector search
  lands – not a magic number left implicit.
- **Generation**: `Generator` protocol with a `StubGenerator` (deterministic, no
  network) and a `DatabricksFMGenerator` (guarded import of `databricks-sdk`, only
  needed once someone runs against a real endpoint). Nothing in `qa.py` depends on
  which one is wired in.
- **Retrieval scoping**: `retrieve()` takes an `offer_id` and only searches that
  offer's corpus – so swapping in real auth later doesn't require touching the
  retrieval boundary.

## §6 PR1b decisions

- **Auth mechanism**: stateless signed magic-link tokens (HMAC-SHA256 over
  `offer_id:expiry`, base64url-encoded), not a login form or session store. Verifying a
  token needs only the shared secret, no directory lookup – matches invariant §1.5 (no
  internal identity pre-day-1) directly instead of building a login system that implies
  one. Secret comes from `PREBOARD_AUTH_SECRET`; falls back to a dev-only constant
  (`auth.py`) so the loop runs without any secret configured. **Must** be set via a
  Databricks secret scope before any real deployment – the fallback is not safe to ship.
- Token TTL defaults to 14 days (offer-to-start-date window), overridable per call.