"""Routes a low-confidence handoff to the department whose directory entry best
matches the question, instead of always the same one recruiter per offer
(PR8/NOTES.md §17).

`UnityCatalogDirectorySource` (PR12/NOTES.md §19, D4) reads `department_contacts` —
it replaces the local `data/directory.md` entirely, not just when Databricks
credentials are configured: routing has no local fallback anymore, since HR editing
a table with an `INSERT` (no redeploy) was the whole point of moving it into UC. It's
shaped like `ChunkSource` (`load(offer_id)`) but ignores the argument — the directory
is one global table, not per-offer — which lets `Router` reuse
`KeywordRetriever`/`EmbeddingRetriever` unmodified instead of a second scoring
implementation. The retriever passed in determines the confidence semantics (token
overlap vs. cosine similarity), exactly like `QA`'s own `confidence_threshold`.
"""
from __future__ import annotations

import json
import re

from preboard.corpus import Chunk
from preboard.handoff import HandoffTarget
from preboard.retrieval import Retriever

DIRECTORY_DOC_ID = "directory"

# Directory entries are short, generic department blurbs, not detailed narrative
# offer-packet text — cosine similarity against them runs meaningfully lower than
# EMBEDDING_CONFIDENCE_THRESHOLD's calibration sample even for a *correct* top-1
# match. Probed against the real endpoint (NOTES.md §17): 5 questions that should
# route scored 0.470-0.637; 3 genuinely unrelated ones scored 0.445-0.501 — the
# ranges overlap, so no threshold separates both perfectly, same structural
# limitation as §13's broad-question case. The call here is the opposite of §13's,
# though: a wrong grounded *answer* is invariant §1.4's real failure mode (the
# candidate believes something false), but a wrong *department* is low-cost — a
# human reroutes it — so this threshold is set to route more often rather than
# default to the generic recruiter, unlike the offer-answer threshold's
# never-guess bias.
ROUTER_EMBEDDING_CONFIDENCE_THRESHOLD = 0.45

_CONTACT_RE = re.compile(r"Contact:\s*(\S+)")
_PERSON_RE = re.compile(r"Person:\s*(.+)")


def _parse_terms(raw: object) -> list[str]:
    """The SQL Statement Execution API doesn't guarantee ARRAY<STRING> columns come
    back as native Python lists in `data_array` — defensively handle a JSON-string
    or a bare list, verified against the real endpoint after department_contacts was
    seeded."""
    if isinstance(raw, list):
        return [str(t) for t in raw]
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        return [str(t) for t in parsed] if isinstance(parsed, list) else []
    except (TypeError, ValueError):
        return [t.strip() for t in str(raw).strip("[]").split(",") if t.strip()]


class UnityCatalogDirectorySource:
    def __init__(self, warehouse_id: str, catalog: str, schema: str):
        from databricks.sdk import WorkspaceClient  # noqa: PLC0415

        self._warehouse_id = warehouse_id
        self._table = f"{catalog}.{schema}.department_contacts"
        self._client = WorkspaceClient()

    def load(self, offer_id: str) -> list[Chunk]:  # offer_id ignored — one global directory
        response = self._client.statement_execution.execute_statement(
            statement=f"SELECT department, person_name, email, routing_terms, covers FROM {self._table}",
            warehouse_id=self._warehouse_id,
            wait_timeout="30s",
        )
        rows = response.result.data_array if response.result else None
        if not rows:
            return []
        chunks = []
        for department, person_name, email, routing_terms, covers in rows:
            terms = ", ".join(_parse_terms(routing_terms))
            text = f"Person: {person_name}\nContact: {email}\nCovers: {covers}\nAlso ask about: {terms}"
            chunks.append(Chunk(doc_id=DIRECTORY_DOC_ID, section=department, text=text))
        return chunks


def _target_from_chunk(chunk: Chunk) -> HandoffTarget:
    contact_match = _CONTACT_RE.search(chunk.text)
    person_match = _PERSON_RE.search(chunk.text)
    contact = contact_match.group(1) if contact_match else "people-operations@dayone.demo"
    name = person_match.group(1).strip() if person_match else chunk.section
    return HandoffTarget(name=name, contact=contact, department=chunk.section)


class Router:
    _DIRECTORY_KEY = "directory"  # cache key only — the source ignores it

    def __init__(self, retriever: Retriever):
        self._retriever = retriever

    def route(self, question: str) -> tuple[HandoffTarget, float] | None:
        results = self._retriever.retrieve(self._DIRECTORY_KEY, question)
        if not results:
            return None
        top = results[0]
        return _target_from_chunk(top.chunk), top.score
