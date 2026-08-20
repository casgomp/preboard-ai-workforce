# preboard

A Q&A buffer for signed-but-not-started hires: answers questions from their offer
packet, hands off the right team when it can't answer confidently, and logs what it
missed. Design rationale, invariants, and decision history live in `NOTES.md` —
this file is just how to run it.

Two front ends share the same Python "brain" (`preboard/`): a Next.js app
(`frontend/`, the primary candidate/HR experience) and a Streamlit app (`app.py`, the
fallback demo surface). Both call the same `QA` orchestration and the same Unity
Catalog schema — see NOTES.md §19 for how they converged.

## Quick start (no Databricks needed)

```bash
pip install -r requirements.txt
python -m preboard.cli --offer-id E001
```

Runs entirely locally against `data/*.md`: keyword-overlap retrieval and a stub
generator that echoes the matched text. No credentials required.

## Running with real Databricks (FM generation, embeddings, Unity Catalog)

1. Copy `.env.example` to `.env` and fill in:
   - `DATABRICKS_HOST` / `DATABRICKS_TOKEN` — your workspace and a personal access
     token
   - `DATABRICKS_WAREHOUSE_ID` (or `DATABRICKS_HTTP_PATH`) — enables the Unity
     Catalog corpus; omit both to keep reading `data/*.md` locally
   - `DATABRICKS_CATALOG` / `DATABRICKS_SCHEMA` — default to `workspace`/`preboard`,
     only needed if your workspace uses different names
   - `PREBOARD_AUTH_SECRET` — omit locally (falls back to a dev-only constant); the
     deployed app uses a real Databricks secret instead (see `databricks.yml`)
2. Run `frontend/databricks/setup_tables.sql` then `seed_data.sql` once against your
   warehouse (creates/seeds `employees`, `department_contacts`, `question_misses`,
   etc. — see `frontend/databricks/README.md`). **Never re-run `seed_data.sql` after
   a demo has started** — its `INSERT OVERWRITE` statements wipe every table they
   touch.
3. Ingest the offer-packet corpus (re-run after editing `data/*.md`):
   ```bash
   python -m preboard.uc_corpus
   ```
4. Run any of the three front ends — all share the same backend:
   ```bash
   python -m preboard.cli --offer-id E001
   streamlit run app.py                # fallback chat UI
   uvicorn server:app --reload         # HTTP API for frontend/'s Next.js app
   ```

`preboard/wiring.py` picks real components automatically whenever credentials are
present — no separate "prod mode" flag.

## Running the full stack (frontend + Python)

```bash
make install   # pip install + npm install, once
make dev        # both processes together; Ctrl-C stops both
```

Or run them separately (equivalent to `make dev`):
```bash
uvicorn server:app --reload           # Python brain, :8000
cd frontend && npm install && npm run dev   # Next.js app, prints its own port
```

If port 8000 is already taken locally, run `make dev PORT=8010` (and set
`PYTHON_API_URL=http://localhost:8010` in `frontend/.env` to match).

Log in as a candidate (`anna.mueller@dayone.demo` / `Welcome5!`, see
`frontend/services/auth/session.ts` for the full demo account list) and ask a
question — `frontend/app/api/documents/ask/route.ts` forwards it to `server.py`
server-to-server, not from the browser, so `PYTHON_API_URL` in `frontend/.env` is a
plain `http://localhost:8000`, no CORS-facing concerns. Log in as HR
(`sarah.weber@dayone.demo` / `PeopleOps!`) to see the "Knowledge gaps" panel.

Other `make` targets: `make test` (both test suites), `make ingest` (re-ingest
`data/*.md` into Unity Catalog), `make deploy` (the Streamlit fallback app to
Databricks Apps).

## Auth

There's no login form on the Python side. A candidate's only credential there is a
signed magic-link token (used by the CLI and the Streamlit fallback):

```bash
python -m preboard.cli --issue-token E001
python -m preboard.cli --token <token>
streamlit run app.py    # then open http://localhost:8501/?token=<token>
```

`--offer-id` is a dev-only bypass that skips token verification — never used in the
deployed app. The Next.js frontend has its own session-cookie auth (see
`frontend/services/auth/session.ts`) — that session, not a preboard token, is the
auth boundary for the `/api/documents/ask` → `server.py` path (NOTES.md §19, D3).

## Tests

```bash
python -m pytest                                  # fast, local, no credentials
RUN_DATABRICKS_INTEGRATION_TESTS=1 python -m pytest tests/test_databricks_integration.py
                                                    # hits the real workspace, needs .env
cd frontend && npm test && npm run typecheck && npm run lint
```

## Deploying to Databricks Apps

```bash
databricks bundle deploy
databricks bundle run preboard
```

Reads `databricks.yml` (app + secret + serving-endpoint/warehouse/UC-table
permissions) and `app.yaml` (the actual run command — Databricks Apps reads this file
directly, not the bundle's `config:` block). This deploys `app.py` (the Streamlit
fallback) only — `frontend/`/`server.py` are local-only in this build (NOTES.md §19).
Check `databricks apps logs preboard` after deploying; see NOTES.md §12 for why that
matters more than it sounds like it should.

## Project layout

- `preboard/` — core logic: `qa.py` (orchestration), `retrieval.py` /
  `embedding_retrieval.py` (keyword vs. real semantic retrieval), `generation.py`
  (stub vs. real FM), `corpus.py` / `uc_corpus.py` (local files vs. Unity Catalog),
  `routing.py` (department handoff routing via Unity Catalog), `auth.py`,
  `wiring.py` (picks real vs. stub components)
- `data/*.md` — sample offer packets (`E001.md` — Anna Müller, `E002.md` — David
  Klein) plus `company.md`, shared company-wide content included for every candidate
- `app.py` — Streamlit chat UI (Databricks App entry point, fallback front end)
- `server.py` — FastAPI HTTP boundary onto the same backend, for `frontend/`
- `preboard/cli.py` — CLI front end, same backend, useful for local dev/testing
- `frontend/` — Next.js app (candidate + HR experience); see `frontend/README.md`
  and `frontend/databricks/README.md`
- `NOTES.md` / `NOTES_ARCHIVE.md` — design log: invariants, deferred work, every
  decision and gotcha behind the code as it exists today
