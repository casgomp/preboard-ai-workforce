# Preboard — fused Day One readiness application

Preboard combines a polished React experience with a Python/Databricks intelligence backend.

- Starting employees see their Day One readiness, schedule, safe updates, and document-grounded answers.
- HR sees readiness across upcoming starters, operational risks, document management, and recurring knowledge gaps.
- Python owns document extraction, audience-filtered retrieval, citations, human handoffs, and the miss log.
- React owns authentication, role-protected pages, readiness presentation, and the user experience.
- The existing Python offer-packet pipeline can use local Markdown or Databricks embeddings, Unity Catalog, and model serving.

All names, credentials, operational records, and documents in this repository are fictional demo data.

## Local setup

Requires Python 3.10+, Node.js 22.13+, and `make`.

```bash
make install
cp .env.example .env
cp frontend/.env.example frontend/.env.local
make dev
```

Open [http://localhost:3000](http://localhost:3000). FastAPI runs privately on `127.0.0.1:8000`; React calls it through authenticated server routes.

The default `PREBOARD_API_SECRET` is for local demonstration only. Before sharing any deployed environment, replace it with the same random value in `.env` and `frontend/.env.local`:

```bash
openssl rand -hex 32
```

## Demo accounts

| Account | Email | Password | Workspace |
|---|---|---|---|
| Starting employee | `anna.mueller@dayone.demo` | `Welcome5!` | Candidate View |
| HR partner | `sarah.weber@dayone.demo` | `PeopleOps!` | HR Control Center |

Each account has exactly one role. There is no combined HR + starter profile.

## Grounded-answer flow

1. React validates the signed login session.
2. Its server route forwards only the verified role and user identifier to FastAPI using the internal service key.
3. Python filters the document library by audience before retrieval.
4. Supported questions return extractive source sentences and citations.
5. Unsupported questions return no invented answer, route to a named team/contact, and enter the knowledge-gap log.
6. HR sees aggregated gaps in the Control Center, without a candidate-level gap view.

Candidate requests cannot retrieve `HR_ONLY` documents. HR document endpoints and knowledge-gap endpoints reject non-HR identities independently of the React interface.

## Repository layout

```text
api/                    FastAPI boundary consumed by React
frontend/               React/Vinext application
preboard/               Python retrieval, routing, auth, storage, and Databricks logic
tests/                  Python unit and API tests
data/                   Local offer packets and company directory
databricks.yml          Databricks bundle definition
scripts/dev.py          Unified local development runner
```

## Tests

```bash
make test
```

The Python suite covers authentication, candidate isolation, retrieval, routing, miss logging, document extraction, API authorization, grounded answers, and knowledge gaps. The frontend suite covers readiness logic, privacy rules, authentication, and the demo workflow.

## Databricks

The existing offer-packet pipeline selects Databricks components automatically when credentials are present. Configure `DATABRICKS_HOST`, `DATABRICKS_TOKEN`, and optionally `DATABRICKS_WAREHOUSE_ID` in `.env`. Without credentials, it runs locally using Markdown, lexical retrieval, and deterministic generation.

The React document library currently uses Python-owned local SQLite and `uploads/`. A later production step can place original files in object storage and replace the Python `DocumentLibrary` implementation with Delta/Vector Search without changing the React API contract.

## Legacy Streamlit interface

`streamlit run app.py` remains available as a backend diagnostic interface. It is not the primary product UI. The React HR Control Center replaces the previously unauthenticated Streamlit gap-report view for normal use.
