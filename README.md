# preboard

A Q&A buffer for signed-but-not-started hires: answers questions from their offer
packet, hands off to HR when it can't answer confidently, and logs what it missed.
Design rationale, invariants, and decision history live in `NOTES.md` —
this file is just how to run it.

## Quick start (no Databricks needed)

```bash
pip install -r requirements.txt
python -m preboard.cli --offer-id jordan-rivera
```

Runs entirely locally against `data/*.md`: keyword-overlap retrieval and a stub
generator that echoes the matched text. No credentials required.

## Running with real Databricks (FM generation, embeddings, Unity Catalog)

1. Copy `.env.example` to `.env` and fill in:
   - `DATABRICKS_HOST` / `DATABRICKS_TOKEN` — your workspace and a personal access
     token
   - `DATABRICKS_WAREHOUSE_ID` — enables the Unity Catalog corpus; omit to keep
     reading `data/*.md` locally
   - `PREBOARD_AUTH_SECRET` — omit locally (falls back to a dev-only constant); the
     deployed app uses a real Databricks secret instead (see `databricks.yml`)
2. If using the Unity Catalog corpus, ingest it once (re-run after editing
   `data/*.md`):
   ```bash
   python -m preboard.uc_corpus --warehouse-id <id>
   ```
3. Run the CLI or the chat UI:
   ```bash
   python -m preboard.cli --offer-id jordan-rivera
   streamlit run app.py    # candidate-facing chat UI, same backend
   ```

`preboard/wiring.py` picks real components automatically whenever credentials are
present — no separate "prod mode" flag.

## Auth

There's no login form. A candidate's only credential is a signed magic-link token:

```bash
python -m preboard.cli --issue-token jordan-rivera
python -m preboard.cli --token <token>
streamlit run app.py    # then open http://localhost:8501/?token=<token>
```

`--offer-id` is a dev-only bypass that skips token verification — never used in the
deployed app.

## Tests

```bash
python -m pytest                                  # fast, local, no credentials
RUN_DATABRICKS_INTEGRATION_TESTS=1 python -m pytest tests/test_databricks_integration.py
                                                    # hits the real workspace, needs .env
```

## Deploying to Databricks Apps

```bash
databricks bundle deploy
databricks bundle run preboard
```

Reads `databricks.yml` (app + secret + serving-endpoint/warehouse permissions) and
`app.yaml` (the actual run command — Databricks Apps reads this file directly, not
the bundle's `config:` block). Check `databricks apps logs preboard` after deploying;
see NOTES.md §12 for why that matters more than it sounds like it should.

## Project layout

- `preboard/` — core logic: `qa.py` (orchestration), `retrieval.py` /
  `embedding_retrieval.py` (keyword vs. real semantic retrieval), `generation.py`
  (stub vs. real FM), `corpus.py` / `uc_corpus.py` (local files vs. Unity Catalog),
  `auth.py`, `wiring.py` (picks real vs. stub components)
- `data/*.md` — sample offer packets (`jordan-rivera.md`, `alex-chen.md`) plus
  `company.md`, shared company-wide content included for every candidate
- `app.py` — Streamlit chat UI (Databricks App entry point)
- `preboard/cli.py` — CLI front end, same backend, useful for local dev/testing
- `NOTES.md` / `NOTES_ARCHIVE.md` — design log: invariants, deferred work, every
  decision and gotcha behind the code as it exists today
