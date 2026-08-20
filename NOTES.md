# NOTES – preboard

Preboarding Q&A buffer for signed-but-not-started hires. Answers questions from the
offer packet and preboarding docs, hands off to HR when it can't, logs what it missed.

Stack: Python, Databricks Free Edition (serverless-only). Generation via a Foundation
Model endpoint (real, PR1d), retrieval via a Databricks embeddings endpoint with
cosine similarity computed in-process (real, PR1d — not a Unity Catalog Vector Search
index; see §9), chat UI as a Databricks App (Streamlit, PR1c), miss log as local SQLite
(stand-in for a UC SQL table).

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
- **Corpus lives in local markdown files, not Unity Catalog** – `EmbeddingRetriever`
  (PR1d) reads `data/*.md` directly; embeddings are computed live per question/offer,
  nothing is persisted in UC. Fine at this corpus size (embeds fast, no caching needed)
  but doesn't match the original "corpus in Unity Catalog" stack claim. TRIGGER: the
  corpus grows enough that per-question embedding latency or cost matters, or the pitch
  needs to show data actually living in UC.

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
- **Live URL**: `https://preboard-7474653684757026.aws.databricksapps.com`. Redeploy
  with `databricks bundle deploy && databricks bundle run preboard` from the repo root
  (needs `DATABRICKS_HOST`/`DATABRICKS_TOKEN` in the shell env, e.g. `set -a; source
  .env; set +a`). Logs: `databricks apps logs preboard --tail-lines 100`.