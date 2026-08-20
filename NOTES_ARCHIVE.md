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
