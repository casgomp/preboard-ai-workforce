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
- **Keyword-overlap retrieval gives false positives on common/incidental words** – hit
  three times now: "your" and recurring proper nouns/dates (fixed via `_STOPWORDS`,
  PR1a), and a single shared content word ("manager") clearing the ratio threshold and
  returning a wrong answer instead of a handoff (fixed via `MIN_OVERLAP_TOKENS`, PR2).
  Both are patches on a scorer that has no real notion of confidence, not a structural
  fix — expect more of these until PR1d lands real vector search. TRIGGER: PR1d.
- **Gap report groups by exact normalized text, not semantic similarity** – two
  differently-phrased versions of the same missed question count as separate rows.
  Fine for a small hackathon demo corpus; would undercount real gaps at scale. TRIGGER:
  PR1d (once embeddings exist, cluster misses by similarity instead of exact match).

## §3 Shipped

- **PR1a** (2026-08-20, `63145d3`) – vertical slice proving ask → grounded answer with
  citation → low-confidence handoff → miss logged, entirely local (keyword-overlap
  retrieval, stub generator, SQLite miss log, CLI front end). No Databricks connection
  required to run or test it. See NOTES_ARCHIVE.md for the design record.
- **PR1b** (2026-08-20, `2f82cc7`) – real per-offer auth via signed magic-link tokens;
  second candidate added so scoping is demonstrable. See NOTES_ARCHIVE.md.
- **PR1c** – Streamlit chat UI, verified against a live local server in a real browser
  (not just unit tests): grounded answer with citation, low-confidence handoff, and
  invalid-token rejection all confirmed rendering correctly. Caught and fixed a real
  concurrency bug in the process — see NOTES_ARCHIVE.md.
- **PR2** – gap report, ranked by frequency, aggregated across all offers (never
  per-cohort — see invariant discussion in §2). Found and fixed a second retrieval
  false-positive while generating demo data for it. See NOTES_ARCHIVE.md.

## §4 Release order

1. PR1a – thinnest vertical slice: one hardcoded offer/candidate, keyword-overlap
   retrieval over one local offer packet (no vector search yet), stub or real FM
   generation behind a swappable interface, fixed confidence threshold, miss log in
   local SQLite (same shape as the eventual UC table), CLI front end (Databricks App
   deferred out of the critical path). Proves ask → grounded answer with citation →
   low-confidence handoff → miss logged end to end without any Databricks credentials.
2. PR1b – real per-offer auth (stateless signed magic-link tokens) and a second
   candidate in the corpus, so auth scoping is actually demonstrable.
3. PR1c – Streamlit chat UI (Databricks Apps-native), reusing the same QA/auth stack
   as the CLI. Runs locally now; becomes a real Databricks App at deploy time with no
   code change.
4. PR1d – swap in real Unity Catalog + vector search retrieval. Blocked on workspace
   credentials.
5. PR2 – gap report, aggregated across all past candidates, ranked by frequency.

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

## §7 PR1c decisions

- **App framework**: Streamlit — resolves the "undecided" note in the stack line.
  Databricks Apps supports it natively, so `app.py` runs unmodified locally
  (`streamlit run app.py`) and once deployed; no separate dev/deploy version.
- **Auth in the UI**: `?token=` query param only, no login form — same magic-link
  token as the CLI, read via `st.query_params`.
- **Gotcha**: `st.cache_resource` caches the `QA`/`MissLog` instance across Streamlit
  reruns, and reruns can land on a different thread than the one that created it.
  `sqlite3.connect()` defaults to `check_same_thread=True`, so the second chat message
  crashed with `sqlite3.ProgrammingError` — invisible to both the CLI (single-threaded)
  and pytest (fresh connection per test), only caught by driving the running app in an
  actual browser. Fixed in `store.py` with `check_same_thread=False` plus a
  `threading.Lock`; regression test in `tests/test_store.py` logs from a spawned
  thread. Also note for future Streamlit hot-reload: editing a module *other than*
  `app.py` doesn't always bust `st.cache_resource` — restart the process, don't trust
  the auto-reload, when a fix doesn't seem to take.

## §8 PR2 decisions

- **Grouping**: normalized exact-text match (lowercase, trim, collapse whitespace,
  strip trailing `?!.`), not semantic clustering — no embedding model exists yet
  (PR1d). Documented as a known undercount, not silently accepted.
- **Aggregation**: always across every `offer_id` in the log, by construction — the
  report has no per-offer or per-cohort view, so it can't accidentally be pointed at a
  near-empty, non-anonymous cohort (see §2's gap-report entry).
- **Retrieval fix, found while seeding demo data for this report**: a single shared
  content word ("manager") was enough to clear `CONFIDENCE_THRESHOLD` and return a
  wrong answer instead of a handoff. Added `MIN_OVERLAP_TOKENS = 2` in `retrieval.py`.