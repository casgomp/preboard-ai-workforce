# NOTES – preboard

Preboarding Q&A buffer for signed-but-not-started hires. Answers questions from the
offer packet and preboarding docs, hands off to HR when it can't, logs what it missed.

Stack: Python, Databricks Free Edition (serverless-only). Generation via a Foundation
Model endpoint (real, PR1d), retrieval via a Databricks embeddings endpoint with
cosine similarity computed in-process (real, PR1d — not a Unity Catalog Vector Search
index; see §9), corpus in a Unity Catalog Delta table (real, PR3 — see §11), chat UI
as a Databricks App (Streamlit, PR1c), miss log as local SQLite (stand-in for a UC SQL
table).

Team of 4, 48-hour hackathon build. Claude writes implementation directly this project
(no local pairing/scaffolding needed) – speed over teaching.

## §1 Durable invariants

1. The bot's only actions are answer, hand off, and log. It never rejects, ranks, or
   writes to an HR system.
2. Pre day-1 makes no anonymity claim. The answerer is HR and already knows the
   candidate by name. The value is volume absorption, not unlinkability. Any token-split
   or k-anonymity work belongs to the day-1 variant, not here.
   **Pitch framing (2026-08-20, §15)**: volume absorption is the mechanism, not the
   value. The signed-to-started gap is when candidates go cold and renege — silence is
   the risk the product addresses. The gap report matters because it's how HR learns
   the packet is silent on exactly the thing an anxious candidate is asking about,
   before it costs them the hire, not just as an FAQ-volume metric.
3. No answer without a retrieved chunk. Every answer is grounded in retrieved doc
   content and names its source document.
4. Low retrieval confidence hands off to a named human. The bot never guesses past its
   corpus.
5. Auth is per-offer and scoped to one candidate. No internal directory identity exists
   at this phase — *within the app's own logic*. The Databricks Apps hosting layer
   mandates SSO for every visitor regardless (platform constraint, not configurable —
   see §10); the pitch is scoped to "any identity can SSO in, the magic-link token is
   what actually scopes access to one offer", not "no login screen at all".

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
- **`KeywordRetriever`'s false-positive weakness is now fallback-only, not fixed** –
  `EmbeddingRetriever` (PR1d) is used whenever Databricks credentials are configured;
  `KeywordRetriever` only runs for teammates without credentials (see `wiring.py`). Its
  known issues ("your", incidental proper nouns, single shared words) are unfixed and
  will resurface for anyone running in stub mode. TRIGGER: n/a — accepted as a
  dev-only fallback, not on the path to fixing.
- **Gap report groups by exact normalized text, not semantic similarity** – two
  differently-phrased versions of the same missed question count as separate rows.
  TRIGGER FIRED: PR1d added real embeddings. Not yet used for gap-report clustering —
  unclaimed follow-up, not done in PR1d.
- **Chunk embeddings still computed live, not persisted** – `UnityCatalogSource` (PR3)
  holds raw chunk text in UC; `EmbeddingRetriever` still calls the embeddings endpoint
  per question rather than reading precomputed vectors from the table. Fine at this
  corpus size. TRIGGER: the corpus grows enough that per-question embedding
  latency/cost matters — store embeddings as a column and only recompute on ingest.
- **T-minus-aware answers**: TRIGGER FIRED, shipped in §16 (PR7) — band-guided
  urgency framing, `--as-of`/`?as_of=` demo override. Not yet re-tuned against real
  usage; band edges are a guess (§16/D4).
- **`preboard/offers.py` start dates are hardcoded, same stub shape as `handoff.py`'s
  target map** – fine for two demo candidates. TRIGGER: n/a for this project's scope;
  a real version reads start date from whatever system issues the offer.
- **Gap report by department (B5)** – now that handoffs carry a department (§17),
  `gap_report.py`/the `?view=gaps` view could group misses by routed department, not
  just aggregate/rank by question text — this is what makes a systemic gap ("everyone
  asks Payroll about bikes and nobody wrote it down") visible on stage. TRIGGER: time
  remains after the core routing loop is solid; ~30 min, mostly `GapEntry` gaining a
  `department` field and one more `st.dataframe` column.
- **`uc_corpus.ingest` globs `data/*.md`, so `directory.md` gets ingested as
  offer_id="directory" rows if UC is re-ingested** – harmless (nothing queries UC with
  that offer_id; `routing.py`'s `DirectorySource` reads the local file directly, not
  UC) but not intentional. TRIGGER: routing moves to UC-backed lookup — filter the
  glob or give directory routing its own table then, not before.

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
- **PR1d** (2026-08-20) – real retrieval (Databricks embeddings endpoint + in-process
  cosine similarity) and real generation (Databricks FM chat endpoint), verified against
  the live workspace via 10 integration tests and a real-browser run — both a grounded
  question and the exact "manager" false-positive from PR2 confirmed fixed under real
  embeddings. Found and fixed a second real SDK bug (typed `ChatMessage`, not raw
  dicts). Graceful fallback to the local stubs when no credentials are configured
  (`wiring.py`), so teammates without a workspace still get a working app. See
  NOTES_ARCHIVE.md.
- **Deploy** (2026-08-20) – `app.py` deployed as a real Databricks App via an Asset
  Bundle (`databricks.yml`), live at
  `https://preboard-7474653684757026.aws.databricksapps.com`. Discovered Databricks
  Apps mandates SSO for every visitor — no public/anonymous access exists — which
  conflicts with the "no login screen" reading of invariant §1.5. Pitch adjusted, not
  the architecture: see §1.5 and §10.
- **PR3** (2026-08-20) – corpus moved into Unity Catalog (`workspace.preboard
  .offer_chunks`, a real Delta table, not a stand-in). `ChunkSource` abstraction
  (`corpus.py`) lets both retrievers read from either UC or local markdown; deployed
  app now uses UC when `DATABRICKS_WAREHOUSE_ID` is configured. Found and fixed a real
  SQL bug: hand-escaped string literals silently dropped apostrophes (Spark SQL
  ignores `''` doubling, unlike ANSI SQL) — switched to parameterized inserts, which
  removes the bug class rather than patching the escaping. See NOTES_ARCHIVE.md.
- **PR4 + critical fix** (2026-08-20) – multi-chunk generation (a broad question can
  now draw on up to 3 supporting sections, not just the single top match) and fixed a
  serious credential-detection bug: `has_databricks_credentials()` only checked
  `DATABRICKS_TOKEN`, but the deployed app authenticates via
  `DATABRICKS_CLIENT_ID`/`DATABRICKS_CLIENT_SECRET` (Databricks Apps' own injected
  OAuth identity) — meaning **the live deployed app had been silently running in local
  stub mode (`KeywordRetriever` + `StubGenerator`) the entire time since first
  deploying**, contradicting everything reported earlier about it using real
  retrieval/generation. Found by adding a startup log line and reading deployed logs,
  not by any test — nothing in the suite runs inside an actual deployed app's
  environment. See §12 and NOTES_ARCHIVE.md.
- **PR5** (2026-08-20) – `data/company.md`, shared non-employee-specific content
  included for every candidate alongside their own offer packet (§14); README.md
  added. Found and fixed a real endpoint hang (`databricks-gte-large-en` never
  returns on batches of ~20+ inputs) surfaced by this being the first time a single
  offer's merged chunk count crossed that threshold — see §14 and NOTES_ARCHIVE.md.
- **PR6** (2026-08-20) – time-aware answers and demo-safety fixes, prompted by a
  pre-demo review: fixed token TTL (14→90 days — was shorter than Alex Chen's own
  46-day signed-to-start gap, so real tokens could expire before day one); resolved
  the offer packet's start-date-relative phrasing into concrete dates via a new
  `preboard/offers.py` + `QA._date_context`; added a countdown caption and a
  `?view=gaps` Streamlit view for the gap report (previously only reachable via local
  CLI, undemoable from the deployed app); wrapped `app.py`'s answer call in
  try/except so an FM timeout degrades to a handoff instead of a traceback on stage.
  See §15 and NOTES_ARCHIVE.md.
- **PR7** (2026-08-20) – T-minus-banded answer urgency: the same equipment question
  now reads as reassuring ("no need to worry yet") at T-105 and urgent ("reach out
  now") at T-3, verified against the real FM endpoint. Added `--as-of`/`?as_of=` demo
  override so this is showable without waiting real days between the two answers.
  See §16 and NOTES_ARCHIVE.md.
- **PR8** (2026-08-20) – department-routed handoffs: a low-confidence question now
  routes to whichever team's `data/directory.md` entry it best matches (`routing.py`,
  a `HandoffTarget.department` field), instead of always the same one recruiter per
  offer — falls back to the recruiter when no department is confident. Found and
  fixed a real threshold-reuse bug: `EMBEDDING_CONFIDENCE_THRESHOLD` (tuned for
  offer-packet text) was silently too high for the directory's short blurbs, so the
  router never fired against the real endpoint until probed and given its own
  threshold. Verified live: "Can I expense a bike?" → Payroll & Benefits, "My laptop
  never arrived" → IT & Equipment. See §17 and NOTES_ARCHIVE.md.

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
4. PR2 – gap report, aggregated across all past candidates, ranked by frequency.
5. PR1d – real retrieval (Databricks embeddings endpoint, in-process cosine
   similarity — not a Unity Catalog Vector Search index, see §9) and real generation
   (Databricks FM chat endpoint), with graceful fallback to local stubs when no
   credentials are configured.

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
- Token TTL defaults to 90 days (offer-to-start-date window), overridable per call —
  was 14 days until §15 (2026-08-20), which was shorter than the sample data's own
  46-day gap for Alex Chen.

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

## §9 PR1d decisions

- **No Unity Catalog Vector Search index** – a managed index needs a Delta table, a
  sync pipeline, and a provisioned Vector Search endpoint; real setup and query
  latency for a corpus that's a handful of chunks per offer. `EmbeddingRetriever`
  (`embedding_retrieval.py`) calls the `databricks-gte-large-en` embeddings endpoint
  directly and computes cosine similarity in-process instead. Deferred to §2 if the
  corpus outgrows this.
- **`EMBEDDING_CONFIDENCE_THRESHOLD = 0.62`, empirically tested, not guessed** – 11
  probe questions (6 grounded, 5 not) against the real endpoint did NOT separate
  cleanly: grounded scores ranged 0.576-0.757, ungrounded 0.392-0.602, overlapping in
  0.58-0.62. 0.62 sits just above every ungrounded score in the sample; the one
  grounded question that falls short triggers a handoff, not a wrong answer — the safe
  side of invariant §1.4. Small sample; `tests/test_databricks_integration.py` is the
  executable record and should be re-run (`RUN_DATABRICKS_INTEGRATION_TESTS=1`) if the
  embedding model or corpus changes enough to be worth re-checking.
- **Graceful fallback, not a hard dependency**: `wiring.py` picks `EmbeddingRetriever`
  + `DatabricksFMGenerator` when `DATABRICKS_HOST`/`DATABRICKS_TOKEN` are set, else
  `KeywordRetriever` + `StubGenerator`. A teammate without workspace access still gets
  a working (locally-scored) app; the Streamlit UI shows a "local stub mode" caption
  when falling back.
- **Credentials via `.env`, gitignored** – loaded with `python-dotenv` in `cli.py` and
  `app.py`. `DATABRICKS_FM_ENDPOINT` is optional, defaulting to
  `databricks-meta-llama-3-3-70b-instruct`.
- **Real SDK bug found, not a config error**: `WorkspaceClient().serving_endpoints
  .query(messages=[...])` needs `databricks.sdk.service.serving.ChatMessage` objects,
  not raw `{"role": ..., "content": ...}` dicts — the dict form fails with
  `AttributeError: 'dict' object has no attribute 'as_dict'`. Only surfaced once the
  generator was actually called against a live endpoint; no unit test would have
  caught it since `StubGenerator` never touches the SDK.

## §10 Deploy decisions

- **Asset Bundle, not ad-hoc `apps create`/`apps deploy`**: `databricks.yml` declares
  the app, the auth secret, and `CAN_QUERY` permission on both serving endpoints
  (`fm_chat`, `fm_embeddings`) in one file — `databricks bundle deploy` then
  `databricks bundle run preboard` reproduces the whole deployment, not just the code
  push. `sync.exclude` keeps `.env`/`.git`/`misses.db`/`__pycache__` off the workspace.
- **A literal `app.yaml` is required in the source root** – the bundle's
  `resources.apps.preboard.config` block (command, env) looked like it should configure
  the app but didn't take effect; the deployed app ran `python app.py` instead of
  `streamlit run app.py` and crashed immediately (Streamlit needs its own runner, not a
  bare Python invocation). Fixed by adding `app.yaml` at the repo root with `command`
  and `env` — that's what Databricks Apps actually reads. The bundle's `config:` block
  may only seed a template, not override an existing file; not fully resolved which,
  but the working setup is: `app.yaml` is authoritative, `databricks.yml` handles
  resources/permissions.
- **`PREBOARD_AUTH_SECRET` is a real Databricks secret** (scope `preboard`, key
  `auth_secret`), injected via `app.yaml`'s `valueFrom` — not the dev fallback constant.
  Secrets are write-only from the CLI (can't be read back), so local `.env` mirrors the
  same value for minting matching test tokens with `preboard.cli --issue-token`.
  Rotate both together (`databricks secrets put-secret` + update `.env`) if either
  needs to change.
- **SSO is mandatory for Databricks Apps, not configurable** – confirmed in docs:
  "Databricks apps do not support public access or anonymous usage, and single sign-on
  is mandatory." Every visitor to the app URL hits a Databricks account login page
  (Google/Microsoft/email — any identity, not only workspace members) before the
  `?token=` magic link is ever evaluated. This is a platform constraint, not a bug —
  see §1.5's amendment. Team decision (2026-08-20): keep it as a Databricks App and
  adjust the pitch language rather than rehost elsewhere under time pressure; revisit
  if the pitch needs "truly no login screen" to hold literally.
  **Session-dependent, not actually gone**: a browser already holding a Databricks
  session (e.g. the workspace creator's own laptop) sees no login form — SSO resolves
  silently — which can make a live demo *look* seamless. A cold device (any real
  candidate, most judges opening the link fresh) still hits the login page. Don't pitch
  it as "no login required" on the strength of a demo run from an already-authenticated
  browser; that's a different, false claim from "the token scopes access to one offer."
- **Live URL**: `https://preboard-7474653684757026.aws.databricksapps.com`. Redeploy
  with `databricks bundle deploy && databricks bundle run preboard` from the repo root
  (needs `DATABRICKS_HOST`/`DATABRICKS_TOKEN` in the shell env, e.g. `set -a; source
  .env; set +a`). Logs: `databricks apps logs preboard --tail-lines 100`.

## §11 PR3 decisions

- **`ChunkSource` protocol** (`corpus.py`): `LocalMarkdownSource` and
  `UnityCatalogSource` (`uc_corpus.py`) both return `list[Chunk]` for an offer id.
  `KeywordRetriever` and `EmbeddingRetriever` take a `ChunkSource` instead of a raw
  `corpus_dir` — neither retriever knows or cares which backend it's reading from,
  matching the existing pattern of swappable boundaries (`Retriever`, `Generator`).
- **Table**: `workspace.preboard.offer_chunks` (offer_id, doc_id, section, text,
  chunk_order), in the default `workspace` catalog Free Edition provisions — no new
  catalog created. Queried through the workspace's serverless SQL warehouse
  (`DATABRICKS_WAREHOUSE_ID` — id `43f29df3c2e0da1d` in this workspace) via
  `WorkspaceClient().statement_execution`, not the `databricks-sql-connector` package
  (one fewer dependency; adequate for a handful of parameterized statements).
  `EmbeddingRetriever` still caches chunks per offer per process, so a UC-backed
  retriever incurs at most one warehouse round trip per offer per run, not one per
  question.
- **Ingestion**: `python -m preboard.uc_corpus --warehouse-id <id>` reads every
  `data/*.md`, deletes and reinserts the table's rows — idempotent, safe to re-run
  after editing a local offer packet. Not run automatically; someone re-ingests by
  hand when the corpus changes. `ensure_schema_and_table` creates the schema/table if
  missing, so a fresh workspace only needs the one command.
- **Real bug: hand-escaped SQL silently corrupted data, not an error** — the first
  version built one large `INSERT ... VALUES (...), (...), ...` statement, escaping
  embedded quotes with SQL-standard `''` doubling. Spark SQL doesn't honor that inside
  a single-quoted string literal; it strips the sequence rather than erroring, so
  `"hasn't"` silently round-tripped as `"hasnt"` — verified directly with a throwaway
  test table (`'hasn''t'` → `'hasnt'`; `'hasn\'t'` → `"hasn't"`, confirming Spark SQL
  wants `\'`, not the ANSI-standard doubling). No exception, no failed test until
  `tests/test_databricks_integration.py::TestUnityCatalogSource` compared UC-read
  chunks against the local files character-for-character. Fixed by switching to
  parameterized inserts (`StatementParameterListItem`, one row at a time) instead of
  hand-rolling escaped SQL — removes the bug class rather than fixing the escape
  character, and matches how `UnityCatalogSource.load()` already queried safely.
  **Lesson for future SQL string-building against this workspace: prefer parameters,
  don't assume ANSI-SQL escaping rules hold.**

## §12 PR4 + credential-detection fix

- **Multi-chunk generation**: `qa.py` now passes up to `MAX_SUPPORTING_CHUNKS = 3`
  chunks to the generator, not just the top match — any chunk scoring at least
  `SUPPORTING_SCORE_RATIO = 0.6` of the top chunk's score qualifies. `Answer.citations`
  is a list now (was singular `source_doc`/`source_section`); `Generator.generate`
  takes `list[Chunk]`. Motivated by a real observed failure: "what do I need to do
  before I start?" was answered from only the "Equipment" section, missing the photo-ID
  and background-check information that live in other sections. `StubGenerator` joins
  chunk texts; `DatabricksFMGenerator`'s prompt was also rewritten to ask for a
  synthesized, natural answer instead of "answer using this excerpt" — the earlier
  prompt tended to produce paraphrase-shaped excerpt dumps rather than direct answers.
- **The credential-detection bug (critical, found by luck, not process)**: `wiring.py`'s
  `has_databricks_credentials()` checked only `DATABRICKS_HOST` and `DATABRICKS_TOKEN`.
  Databricks Apps inject `DATABRICKS_CLIENT_ID`/`DATABRICKS_CLIENT_SECRET` for the
  app's own OAuth identity — never `DATABRICKS_TOKEN`. Every deployment since the app
  first went live (`6c5a76e` onward, including the PR3/Unity Catalog work) had this
  check silently evaluating to `False` inside the deployed app, meaning it ran
  `KeywordRetriever` + `StubGenerator` + whatever `LocalMarkdownSource` fallback the
  code path picked, **not** the real embeddings/FM/UC path every prior NOTES entry
  claimed was live and verified there. Local CLI testing was never affected (`.env` has
  a real `DATABRICKS_TOKEN`), which is exactly why it went unnoticed — every "verified
  against the live workspace" claim before this was true for local `.env`-based runs,
  not for the deployed app specifically.
  **How it surfaced**: the user pasted a real answer from the deployed app that read
  as verbatim chunk text rather than an LLM paraphrase; a diagnostic startup log line
  (`app.py`, temporary, replaced with a permanent one-line version) confirmed
  `has_databricks_credentials()` was `False` in the deployed environment via
  `databricks apps logs`.
  **Fix**: `has_databricks_credentials()` now accepts either the PAT path
  (`DATABRICKS_TOKEN`) or the OAuth path (`DATABRICKS_CLIENT_ID` +
  `DATABRICKS_CLIENT_SECRET`), alongside `DATABRICKS_HOST` either way. Regression
  tests in `tests/test_wiring.py` cover all four combinations, including the specific
  broken one. `app.py` keeps a permanent one-line startup log
  (`[preboard] real Databricks components: {bool}`) so this class of silent fallback
  is visible in `databricks apps logs` without needing to SSO into the app to check.
  **Standing lesson**: nothing in the test suite runs inside an actual deployed
  Databricks App's environment — local `.env`-based tests and integration tests both
  use PAT auth, which structurally cannot catch an OAuth-path-only bug. If a future
  change depends on distinguishing "local dev" from "deployed app," don't trust local
  testing to validate it — check `databricks apps logs` after deploying, every time.

## §13 Broad-question threshold tradeoff (accepted, not fixed)

- **Finding**: "What do I need to do before I start?" is a genuinely broad question —
  its answer is spread across several sections, so no single chunk's cosine similarity
  to it scores high, even after adding a purpose-written "Before your first day
  checklist" section to both offer packets (`jordan-rivera.md`, `alex-chen.md`). That
  section correctly became the top-ranked chunk (was "Equipment" before), but only
  reached 0.581/0.526 — still under `EMBEDDING_CONFIDENCE_THRESHOLD = 0.62`.
- **Why the threshold wasn't just lowered**: a fuller probe showed the grounded and
  ungrounded score ranges now genuinely overlap. "Can I negotiate a higher salary
  before I start?" — ungrounded, the corpus has nothing about negotiation — scores
  0.602, *higher* than either broad "before I start" question. No single threshold
  separates both correctly; lowering it to let the broad question through would also
  let that ungrounded question through and produce a confidently wrong answer instead
  of a handoff, which is the worse failure per invariant §1.4.
- **Decision (2026-08-20, team call)**: keep `EMBEDDING_CONFIDENCE_THRESHOLD = 0.62`.
  Broad multi-topic questions will sometimes hand off to HR even when the corpus
  technically contains the answer, in favor of never confidently answering an
  unanswerable one. Framed as a deliberate safety property for the pitch ("the bot
  would rather escalate than guess"), not a known bug. The "Before your first day
  checklist" sections stay — they're still a real ranking improvement and would help
  further if the threshold or embedding model changes.
- **Structural limitation, not a tuning problem**: single-chunk cosine similarity has
  a ceiling on how well it can serve broad/aggregate questions by design — the whole
  approach retrieves and grounds on one topical unit at a time. A future fix (not
  attempted here) would need query decomposition or multi-pass retrieval, not just a
  different threshold or more corpus content.

## §14 Shared company-wide corpus, and a real endpoint hang

- **`data/company.md`**: non-employee-specific content (mission/values, office
  policy, code of conduct, IT/security basics, expense policy, holidays, L&D,
  performance reviews, who to contact) — the kind of thing a real company hands every
  new hire regardless of their specific offer. `corpus.py`'s `SHARED_DOC_ID = "company"`
  is included alongside every offer's own chunks by both `LocalMarkdownSource` and
  `UnityCatalogSource`, not instead of them. An offer id with no dedicated doc still
  gets shared content — not a security gap, since company info isn't candidate-specific
  and the real auth boundary is `verify_token()`, not this fallback (see updated tests
  in `test_retrieval.py`/`test_qa.py`).
- **Real endpoint bug found while testing this**: `databricks-gte-large-en` hangs —
  no error, no SDK timeout, it simply never returns — on a single `query()` call
  batching around 20+ inputs. Reproduced with both real chunk text and trivial short
  strings ("test sentence number N" × 20), which ruled out payload size as the cause;
  it's an item-count limit. Surfaced because `company.md` pushed a single offer's
  merged chunk count (offer-specific + shared) past 20 for the first time — every
  prior test and demo had stayed under it by coincidence. Fixed by sub-batching in
  `EmbeddingRetriever._embed` (`MAX_EMBED_BATCH_SIZE = 10`); regression test
  (`test_embedding_batches_larger_than_the_endpoint_limit`) uses a fake `ChunkSource`
  of 25 chunks so it doesn't depend on the real corpus staying above the limit.
  **This would have been a silent full outage of every answer** (not a wrong answer,
  not a bad handoff — every single question hangs indefinitely) the first time a
  real corpus grew past ~20 chunks for one offer, with no error to point at. Worth
  remembering for any future endpoint integration: an API that hangs instead of
  erroring on an oversized request is a real failure mode to test for, not just
  size/rate-limit errors.
- **Ordering gotcha**: `UnityCatalogSource`'s original `ORDER BY offer_id` put shared
  chunks before offer-specific ones for `jordan-rivera` (alphabetically "company" <
  "jordan-rivera") but after them for `alex-chen` ("alex-chen" < "company") —
  inconsistent with `LocalMarkdownSource`'s fixed offer-then-shared order, and caught
  by `test_reads_the_same_chunks_as_the_local_files` comparing the two exactly. Fixed
  with `ORDER BY CASE WHEN offer_id = :offer_id THEN 0 ELSE 1 END, chunk_order`.

## §15 PR6: time-awareness and demo-safety fixes

Prompted by a pre-demo review pointing out the build was a grounded Q&A bot but
nothing in it knew what day it is or when a candidate starts — a real gap given the
product's own "countdown to day one" framing, and one bug that made the framing
actively false.

- **TTL bug (real, not hypothetical)**: `DEFAULT_TTL_SECONDS` was 14 days, but the
  sample data's own start dates are 25 days out (Jordan) and 46 days out (Alex) from
  a token issued today. A token minted at offer-signing would already be dead well
  before day one for either sample candidate — the demo data contradicted the demo's
  own auth window. Bumped to 90 days; still a stub constant, not derived from any
  actual notice-period distribution, but covers the sample data with margin.
- **Date resolution, not full T-minus-aware content**: the offer packets are full of
  start-date-relative phrasing ("about a week before your start date", "by the
  Wednesday before you start") that the pipeline had no way to resolve — neither
  `qa.py` nor `generation.py` looked at any date. Added `preboard/offers.py` (stub
  offer_id → start_date lookup, same shape as `handoff.py`'s target map) and
  `QA._date_context()`, which computes a plain-language line ("Today's date is
  2026-08-20. This candidate's start date is 2026-09-14, which is in 25 days.") and
  passes it to `Generator.generate` as a new optional `date_context` parameter.
  `DatabricksFMGenerator`'s prompt now instructs the model to resolve relative
  phrasing into a concrete date/day-count when that line is present; `StubGenerator`
  ignores it (no LLM to do the resolving). This is date arithmetic on top of the
  existing single-pass retrieval, not the stronger "answer changes by T-minus band"
  idea (nothing to do at T-60 vs. escalate now at T-3) — that's deferred in §2 as a
  distinct, larger piece of work.
- **`app.py` had no error handling around the one call that hits the network on every
  question** (`get_qa().ask(...)`) — an FM timeout or a permission blip would have
  rendered a raw traceback mid-demo. Wrapped in try/except; on any exception it logs
  to stdout (`databricks apps logs`) and degrades to the same handoff message as a
  low-confidence miss, per invariant §1.4's "never guess, escalate instead" default —
  this is a caught-exception fallback, not itself a MissLog entry, since it isn't a
  retrieval-confidence signal.
- **Gap report wasn't demoable from the deployed app** — `gap_report.py` was a local
  CLI reading `misses.db`, but that file lives in the deployed container's ephemeral
  filesystem, unreachable via CLI once deployed. Added a second Streamlit view
  (`app.py`'s `main()` branches on `?view=gaps`, not behind the offer token — this is
  an internal HR view, not the candidate-facing flow) that renders the same
  `gap_report()` function's output as a table. Both views share one `app.py`/one
  deploy; no new auth mechanism.
- **Countdown caption**: `?view=gaps` aside, the normal chat view now shows "You
  start in N days (Month D, YYYY)" under the title, sourced from the same
  `preboard/offers.py` lookup — makes the countdown framing visible on the page
  itself, not just in answer text.

## §16 PR7: T-minus-banded answer urgency

§15 resolved the offer packet's relative timing phrases into concrete dates. This
made the *content* itself change with T-minus — the same equipment question should
read as "nothing to worry about yet" a few months out and "escalate now" days out,
not just report a different date in the same neutral tone.

- **D1 — banded prompt guidance, not per-band corpus content**: a per-band
  instruction appended to the existing `date_context` line reuses §15's plumbing
  entirely (constants + a longer prompt instruction); per-band corpus content would
  need every question-worthy topic multiplied by band and a retrieval change to pick
  among them — out of scope for the time available. `_TMINUS_BANDS` /
  `_TMINUS_OVERDUE_GUIDANCE` in `qa.py`; `_tminus_guidance(delta_days)` returns the
  first band whose threshold `delta_days` clears, checked in descending threshold
  order.
- **D2 — band selection lives in `qa.py`, not `offers.py`**: `offers.py` stays pure
  data (start dates only); banding is prompt policy, alongside the rest of
  `_date_context`'s prompt-shaping logic.
- **D3 — `as_of` override for demoing without waiting real days**: `QA.ask(...,
  as_of: date | None)`, CLI `--as-of YYYY-MM-DD`, Streamlit `?as_of=YYYY-MM-DD`. Only
  reaches the prompt string built in `_date_context` — confirmed it does not touch
  `MissLog.log_miss` or `verify_token`, so an unauthenticated, guessable query param
  carries no security weight here; it's a demo/testing knob, not a bypass of
  anything.
- **D4 — band edges (60 / 14 / 4 days) are a guess, not tuned**: chosen to roughly
  match the corpus's own stated lead times ("about a week", "ten days", "three
  business days before you start"), unlike `EMBEDDING_CONFIDENCE_THRESHOLD` which
  was probed against real scores (§9). Worst case if a boundary is wrong: a
  slightly-off tone, not a wrong fact — retrieval and grounding are untouched by this
  PR. Named as a guess rather than presented as calibrated.
- **Verified against the real FM endpoint** (not just the deterministic band-
  selection unit tests in `tests/test_qa.py`, which don't and can't test LLM
  compliance): "When does my laptop arrive?" for `jordan-rivera` at `--as-of
  2026-06-01` (T-105) answered "there's no need to worry about it just yet... the
  laptop shipment hasn't started its lead time... everything is on track"; the same
  question at `--as-of 2026-09-11` (T-3) answered "that's already passed... it's
  likely overdue... you should reach out to them now to inquire about the status."

## §17 PR8: department-routed handoffs

Every low-confidence question had always handed off to the same one stub recruiter
per offer (`handoff.py`, unchanged since PR1a), regardless of what the question was
about — a bike-expense question and a background-check question went to the same
person. This routes to the department whose `data/directory.md` entry best matches
the question instead.

- **`DirectorySource` reuses `ChunkSource`'s shape but ignores `offer_id`** — the
  directory is one global document, not per-offer — which lets `Router` wrap
  `KeywordRetriever`/`EmbeddingRetriever` unmodified rather than a second scoring
  implementation. `Router.route(question)` returns `(HandoffTarget, score) | None`;
  `_target_from_chunk` parses a `Contact: <email>` line out of the matched chunk's
  text to build the target, with the department name as both `HandoffTarget.name` and
  the new `HandoffTarget.department` field (`None` for the plain per-offer fallback).
- **`QA._route`**: on a low-confidence question, tries the configured `router` first
  (if `score >= router_threshold`) and falls back to `handoff_target(offer_id)`
  otherwise — same never-guess-past-confidence shape as invariant §1.4, applied to
  *which human* gets the handoff, not just whether to answer. `router`/
  `router_threshold` are optional constructor args (default `None`/`0.0`), so every
  existing `QA(...)` call site and test is unaffected.
- **`wiring.build_router(corpus_dir)`** mirrors `build_retriever`'s credential check
  (embedding-scored router when Databricks credentials are configured, keyword-scored
  otherwise) and is wired into both `app.py` and `cli.py`.
- **Real bug found by testing against the live endpoint, not by the unit tests**: the
  first version reused `EMBEDDING_CONFIDENCE_THRESHOLD` (0.62) for the router. Every
  routing attempt against the real endpoint fell back to the generic recruiter —
  the router was silently never firing. Probed directly: 5 questions that *should*
  route scored 0.470-0.637 against their correct department; 3 genuinely unrelated
  ones scored 0.445-0.501. Two findings from that probe:
  - **The offer-packet threshold doesn't transfer**: directory entries are short,
    generic department blurbs, not detailed narrative offer-packet text, so even a
    *correct* top-1 match scores lower than the sample `EMBEDDING_CONFIDENCE_THRESHOLD`
    was calibrated against (§9).
  - **The confident/unconfident ranges overlap here too** (0.470-0.637 vs.
    0.445-0.501), the same structural shape as §13's broad-question finding — but the
    call is the opposite of §13's, because the stakes are different. §13 kept a
    conservative threshold because a wrong grounded *answer* is invariant §1.4's real
    failure mode: the candidate believes something false. A wrong *department* is
    low-cost — a human on the receiving end reroutes it — so `ROUTER_EMBEDDING_
    CONFIDENCE_THRESHOLD = 0.45` (routing.py) is set to route more often, accepting
    some misroutes (e.g. "Will I get stock options?" would confidently route to
    People Ops) in exchange for the bike question actually reaching Payroll instead of
    always the recruiter. Small sample, same caveat as §9 — revisit if real usage
    shows misrouting is more disruptive than assumed here.
- **Verified against the real embeddings endpoint after the fix**: "Can I expense a
  bike?" (jordan-rivera) → Payroll & Benefits, 0.47 match; "My laptop never arrived,
  who do I contact?" (alex-chen) → IT & Equipment, 0.58 match.
- **Deferred (B5, §2)**: gap report grouped by routed department, not just question
  text — the next ~30 min of work, and what turns this into a demoable "here's what
  Payroll doesn't have written down" moment rather than just a UX nicety.
- **Scope note**: `data/directory.md` is read locally by `DirectorySource`, not
  through `UnityCatalogSource` — routing doesn't go through Unity Catalog at all yet.
  `uc_corpus.ingest`'s `data/*.md` glob will pick it up as harmless, unused
  `offer_id="directory"` rows if UC is re-ingested (see §2).
  Same corpus, same retrieval, only the injected date/band guidance changed.