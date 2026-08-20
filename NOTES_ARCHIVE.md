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
