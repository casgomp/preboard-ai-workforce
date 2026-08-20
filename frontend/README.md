# Day One Digital Twin

Local hackathon MVP for **From Candidate to Colleague — Countdown to Day One**. All people, companies, operational records, credentials, and policies are fictional demo content.

The application gives a starting employee a clear Day One readiness view and gives HR a separate control center for preparation risks. It also accepts company documents, extracts searchable passages, and answers free-text questions strictly from those passages. Every supported answer includes a citation. If the local document library cannot support an answer, the application abstains and routes the user to the accountable department and contact.

## Run locally

Requires Node.js 22.13 or newer.

```bash
npm install
cp .env.example .env.local
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

The development runtime creates local SQL and object-storage bindings automatically. Uploaded files, extracted text, document metadata, and passages are kept in the project-local Wrangler state under `.wrangler/`; no hosted website or Sites project is required.

## Demo accounts

Each account has exactly one workspace.

| Account | Email | Password | Destination |
|---|---|---|---|
| Starting employee | `anna.mueller@dayone.demo` | `Welcome5!` | Candidate View |
| HR partner | `sarah.weber@dayone.demo` | `PeopleOps!` | HR Control Center |

## Main routes

- `/` — local login
- `/candidate` — candidate-safe readiness, schedule, updates, and grounded document questions
- `/hr` — readiness operations, risk controls, and company document management
- `/hr/employees/E001` — full employee fact detail and traceability
- `/api/demo` — authenticated readiness snapshots and HR-only demo mutations
- `/api/documents` — HR-only document inventory and upload/extraction
- `/api/documents/ask` — authenticated and audience-filtered grounded retrieval

## Demo sequence

1. Sign in as Anna and ask a free-text question. The answer cites its source document.
2. Ask something unavailable, such as today’s cafeteria menu. The application abstains and routes the question to Facilities.
3. Sign out and sign in as Sarah. Upload a text or PDF policy and inspect the extracted passage count.
4. Simulate an IT delay. The laptop changes from ready to delayed, the readiness score drops, a high risk appears, and history records the source change.
5. Sign back in as Anna. The candidate message remains safe and does not expose HR-only operational notes.

## Local storage and Databricks

`DOCUMENT_MODE=local` uses the local `DB` SQL binding for document metadata and passages and the local `DOCS` object bucket for original files. `DATA_MODE=mock` keeps the repeatable readiness scenario in the running process.

Databricks remains optional. To use it, run `databricks/setup_tables.sql` and `databricks/seed_data.sql`, configure the `DATABRICKS_*` values in `.env.local`, and set `DATA_MODE=databricks` and/or `DOCUMENT_MODE=databricks`. The Databricks document adapter stores extracted content, chunks, ownership, and audience controls in Delta while retaining original files in the local object bucket.

The grounded question-answering path is extractive rather than generative: document sentences are retrieved, cited, and returned only when the support threshold is met. Candidate queries cannot retrieve HR-only documents.

## Verification

```bash
npm test
npm run typecheck
npm run lint
npm run build
```

## Current limitations

- Demo accounts are stored locally with password hashes and signed session cookies. A real rollout should replace them with company SSO.
- Readiness simulation state resets when the local process restarts.
- The Databricks transport is implemented but requires a real workspace and its credentials for verification.
- Grounded retrieval uses lexical matching. Databricks Vector Search can later provide semantic retrieval while preserving citations and abstention.
