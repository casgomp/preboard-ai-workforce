# NOTES_ARCHIVE – preboard

## PR1a – vertical slice (2026-08-20, `63145d3`)

**Why:** Prove the answer → handoff → log loop end to end before touching any Databricks
service, so the demo doesn't depend on workspace/credential setup being ready on day one
of a 48-hour build.

**Design:** `Retriever`, `Generator`, and `MissLog` are the three boundaries meant to
absorb PR1b without touching `qa.py`. Retrieval scores by token overlap over
`## `-delimited markdown sections (no embeddings); the threshold is a named constant,
not implicit. Generation and the miss-log backend are swappable by construction — the
CLI wires `KeywordRetriever` + `StubGenerator` + SQLite `MissLog` together, and nothing
else in the codebase assumes those choices.

**Gotchas resolved:** the keyword-overlap scorer initially false-positived on pronouns
("your") and incidental proper nouns/dates that recur across every section — two test
failures during PR1a surfaced this before it reached a demo. Fixed by widening the
stopword list; flagged in NOTES.md §2 as a known weakness of the stand-in scorer, not a
solved problem, since real vector search (PR1b) is what actually fixes the failure mode.

**Deferred, unlocked by this merge:** PR1b (real Unity Catalog + vector search
retrieval, real per-offer auth, Databricks App UI) and PR2 (gap report) both build on
this loop and are now unblocked.

## PR1b – real per-offer auth (2026-08-20, `2f82cc7`)

**Why:** The hardcoded `--offer-id` in PR1a couldn't demonstrate invariant §1.5
(per-offer scoping, no internal identity) or survive an obvious pitch question — "how
does a candidate get in without company credentials?"

**Design:** Stateless HMAC-signed magic-link tokens (`auth.py`), not a login form or
session store — verification needs only the shared secret, matching "no internal
identity" directly. Added a second candidate (`alex-chen`) since auth/retrieval scoping
isn't demonstrable with only one offer in the corpus.

**Deferred, unlocked by this merge:** the Databricks App UI can now build a real
token-gated flow instead of stubbing auth (see PR1c).

## PR1c – Streamlit chat UI (2026-08-20)

**Why:** Resolves the "app framework undecided" note that's been sitting in the stack
line since NOTES.md was first written; a working chat UI matters more for a hackathon
pitch than any backend polish.

**Design:** Streamlit, since Databricks Apps supports it natively — `app.py` runs
identically local and deployed. Auth reads `?token=` via `st.query_params`, no login
form, reusing `preboard.auth` unchanged from the CLI.

**Gotchas resolved:** manual browser testing (not pytest) caught a real concurrency
bug — `st.cache_resource` held a `MissLog` whose `sqlite3` connection was thread-affine
by default, and Streamlit reruns can land on a different thread per interaction. First
message worked, second crashed with `sqlite3.ProgrammingError`. Fixed with
`check_same_thread=False` plus a `threading.Lock` in `store.py`; regression test added.
Also hit a false-fix: editing `store.py` didn't bust Streamlit's `st.cache_resource`
cache via hot-reload, so the old broken connection kept getting served until the
process was restarted — worth remembering next time a fix "doesn't take" in a running
Streamlit session.

**Deferred, unlocked by this merge:** PR1d (real UC + vector search retrieval) is the
only piece left before the pitch's full architecture is real rather than stubbed.

## PR2 – gap report (2026-08-20)

**Why:** The miss log has been writing since PR1a but nothing read it back. The trigger
in NOTES.md §2 fired once the loop was demoable end to end (PR1a).

**Design:** Ranks misses by frequency, grouped by normalized exact text (case,
whitespace, trailing punctuation only — no semantic clustering, no embedding model
exists yet). Always aggregates across every `offer_id` in the log; there's no
per-cohort view, so it structurally can't be pointed at a near-empty, re-identifying
cohort. `gap_report()` is a pure function over `MissLog.all_misses()`.

**Gotchas resolved:** generating demo data for the report reproduced the same class of
bug as PR1a's stopword issue, one level worse — a single shared content word
("manager") cleared the confidence ratio on an unrelated question for a second
candidate and returned a wrong answer instead of a handoff, which undermines invariant
§1.4 more directly than a stopword miss does. Fixed with a minimum-overlap-count floor
(`MIN_OVERLAP_TOKENS = 2`) alongside the ratio threshold; regression test added. Same
root cause as before — this scorer has no real notion of confidence — and the same
fix pattern: patch cheaply, log it, defer the structural fix to PR1d.

## PR1d – real retrieval and generation (2026-08-20)

**Why:** Everything through PR2 ran on stand-ins (keyword overlap, a stub generator).
Once Databricks credentials were available, this was the last piece needed for the
pitch's architecture to be real rather than simulated.

**Design:** Discovered the workspace has both chat and embeddings serving endpoints
available (pay-per-token Foundation Model APIs), which changed the plan — rather than
standing up a Unity Catalog Vector Search index (a Delta table, a sync pipeline, a
provisioned endpoint: real setup for a corpus this small), `EmbeddingRetriever` calls
`databricks-gte-large-en` directly and computes cosine similarity in-process. Chunk
loading was extracted from `retrieval.py` into `corpus.py` since two retrievers now
share it. `wiring.py` centralizes the real-vs-stub choice for both `cli.py` and
`app.py`, based on whether `DATABRICKS_HOST`/`DATABRICKS_TOKEN` are configured — a
teammate without a workspace still gets a working app, not a crash.

**Gotchas resolved:** two real bugs, neither of which a unit test could have caught
since `StubGenerator`/`KeywordRetriever` never touch the SDK. (1) `serving_endpoints
.query(messages=[...])` needs typed `ChatMessage` objects, not raw dicts — fixed in
`generation.py`. (2) The confidence threshold was assumed to separate cleanly like the
keyword-overlap one had; empirically it didn't (grounded 0.576-0.757, ungrounded
0.392-0.602, overlapping in the middle). Picked 0.62 — just above the ungrounded max —
so the one ambiguous grounded question fails toward a handoff, not a wrong answer.
Documented as a small-sample calibration, not a settled constant, with
`tests/test_databricks_integration.py` (opt-in via `RUN_DATABRICKS_INTEGRATION_TESTS=1`,
since it hits the network and costs tokens) as the executable record. Verified in a
real browser: a grounded question got a real LLM-paraphrased answer with correct
citation, and the exact "manager" false positive from PR2 was confirmed fixed under
real embeddings.

**Deferred, unlocked by this merge:** the corpus itself still lives in local markdown,
not Unity Catalog (§2) — fine at this scale, revisit if it grows. Gap-report semantic
clustering (§2) could now use these same embeddings but doesn't yet — unclaimed
follow-up.

## Deploy — real Databricks App (2026-08-20)

**Why:** Everything up to PR1d ran and was verified locally against real endpoints;
deploying was the last step to make the whole pitch live rather than "runs on my
machine."

**Design:** An Asset Bundle (`databricks.yml`) declares the app, the auth secret as a
real Databricks secret, and `CAN_QUERY` permission on both serving endpoints in one
file — `databricks bundle deploy && databricks bundle run preboard` reproduces the
whole setup, not just a code push.

**Gotchas resolved:** the bundle's `resources.apps.*.config` block (command, env)
looked like it should configure the app but didn't take effect — the deployed app ran
`python app.py` instead of `streamlit run app.py` and crashed immediately. A literal
`app.yaml` at the repo root, which Databricks Apps actually reads, fixed it.

**Finding, not a bug:** Databricks Apps mandates SSO for every visitor — confirmed in
docs, not configurable. Conflicts with invariant §1.5 read as "no login screen exists."
Team decision: keep it as a Databricks App, adjust the pitch to "the magic-link token
scopes access to one offer" rather than "no login required," and note that a demo run
from an already-authenticated browser looks seamless but isn't representative of a
cold visitor's experience.

## PR3 — corpus in Unity Catalog (2026-08-20)

**Why:** The stack line has said "corpus in Unity Catalog" since before any code
existed; PR1d used real FM and embeddings endpoints but still read the corpus from
local markdown files, leaving that specific claim unbacked.

**Design:** `ChunkSource` protocol (`corpus.py`) with `LocalMarkdownSource` and
`UnityCatalogSource` (`uc_corpus.py`) — both retrievers take a source instead of a raw
path, so neither knows or cares which backend it's reading from. Table:
`workspace.preboard.offer_chunks`, queried via the workspace's serverless SQL
warehouse. `wiring.py` picks UC when `DATABRICKS_WAREHOUSE_ID` is configured (on top
of the existing credentials check), local markdown otherwise — same graceful-fallback
shape as the retriever/generator choice in PR1d.

**Gotchas resolved:** the ingestion script's first version built one large
hand-escaped `INSERT ... VALUES` statement, doubling embedded quotes (`''`) per ANSI
SQL convention. Spark SQL doesn't honor that inside a string literal — it silently
strips the sequence instead of erroring, so `"hasn't"` round-tripped as `"hasnt"` with
no exception anywhere. Caught only because the integration test compared UC-read
chunks against the local files character-for-character rather than just checking
"some text came back." Fixed by switching to parameterized inserts, which removes the
escaping question entirely rather than fixing the escape character — the same lesson
as PR1d's `ChatMessage` bug: real network/SQL calls surface failure modes local stubs
structurally cannot.
