# Demo script — PLAN_PR13 B5

Walked cold-start end to end on 2026-08-20 against the real workspace. Every step
below actually ran; the exact requests and responses are in the PR13 session. Read
top to bottom in demo order — the countdown comparison (step 4) is the moment PR7's
work gets to show itself, so don't cut it if time is short.

## Setup

```bash
make dev   # both processes; wait for both "Application startup complete." and
           # "Local: http://localhost:3000/" before starting
```

Login accounts (`frontend/services/auth/session.ts`): only Anna (candidate) and
Sarah Weber (HR) exist — E002-E005 have no login, they're HR-dashboard-only. Don't
try to log in as anyone else.

## 1. Login as the candidate

`anna.mueller@dayone.demo` / `Welcome5!` → lands on `/candidate`.

## 2. A grounded question

Ask: **"When will my laptop arrive?"**

Answer cites Anna's own offer packet (`E001`, "Anna Müller — Offer Packet") — the
"Sources" row shows one badge per distinct document even though up to 3 chunks
from that document may have supported the answer (`server.py` returns one
citation per contributing chunk; the UI dedupes by `documentId` for display, fixed
in this session after showing 3 identical-looking pills for one source). And —
because her real start date is 5 days out — the answer already frames it with
urgency: *"...should be arriving soon... if it hasn't arrived by tomorrow, contact
workplace-it@dayone.demo."* This single answer is doing double duty: it's both the
grounded-citation proof point and a first taste of the T-minus banding, so don't
rush past the phrasing.

## 3. A routed handoff

Ask: **"Is there a gym in the building?"**

No document answers this. Response: `NEEDS_HUMAN`, handed off to **Facilities**
(Laura Stein, facilities@dayone.demo) — the router matched "building" against
Facilities' `covers` text in `department_contacts`, not a hardcoded map. Say that
part out loud; it's the thing that makes this different from a keyword lookup.

## 4. The countdown comparison — PR7's moment

The UI doesn't expose this (by design — `as_of` is a dev-only override, see
`preboard/qa.py`'s docstring), so show it as a terminal aside right after step 2:
same employee, same question, two different `as_of` dates.

```bash
# Far out: reassuring, no urgency
curl -s -X POST http://localhost:8000/ask -H "Content-Type: application/json" \
  -d '{"employee_id":"E001","question":"When will my laptop arrive?","start_date":"2026-11-19","as_of":"2026-08-20"}'
# -> "...scheduled to arrive about one week before your start date... November 12."

# 2 days out: flips to overdue
curl -s -X POST http://localhost:8000/ask -H "Content-Type: application/json" \
  -d '{"employee_id":"E001","question":"When will my laptop arrive?","start_date":"2026-08-22","as_of":"2026-08-20"}'
# -> "...should have arrived... it's likely overdue. You should contact
#     workplace-it@dayone.demo now..."
```

Same question, same corpus chunk, opposite urgency — purely from where the candidate
sits on the calendar. That's the pitch line: this isn't a static FAQ bot.

## 5. HR view

Login as HR: `sarah.weber@dayone.demo` / `PeopleOps!` → `/hr`.

Five employees render (E001-E005), each reading their own offer packet if asked —
verified live for Maria/Lukas/Sofia (E003-E005) after PR13 B3 added their packets.
`DATA_MODE` defaults to `mock` in `frontend/.env` for demo reliability (no
dependency on live workspace connectivity mid-pitch); flip to `DATA_MODE=databricks`
beforehand if you want the readiness view reading real Unity Catalog rows instead —
`DatabricksDataProvider` is fully implemented and verified end-to-end (PR13 B4,
`frontend/.env`'s `DATABRICKS_*` block already has working local credentials). If
you do flip it, say so out loud either way — "mock" or "reading live from Databricks"
— per NOTES.md's rule of not letting a claim about the workspace outrun the code.

## 6. Knowledge gaps panel

Same HR session. The panel is pre-seeded (`python -m preboard.seed_misses`,
PR13 B1) — 24 questions, 4 departments (Workplace IT, Facilities, People
Operations, Learning & Onboarding), plus older "Unrouted" rows from before routing
existed. Don't ask a live unanswerable question here unless you want the count to
visibly tick up in front of the judges — that's a feature, not a risk, if you want
to show it happening live instead.

## Known state to check before presenting

- Your terminal's `make dev` uvicorn may need a restart if it's been running since
  before this session's edits to `server.py`/`preboard/` — `--reload` doesn't always
  survive a large edit batch cleanly. `curl localhost:8000/health` should return
  `{"real_components":true}` in under a second; if it hangs, Ctrl-C and re-run
  `make dev`.
- `question_misses` currently has exactly the 24 PR13 B1 seed rows — re-running
  `python -m preboard.seed_misses` appends another batch rather than replacing it
  (documented in the script itself); don't run it twice before presenting unless you
  want the doubled count.
