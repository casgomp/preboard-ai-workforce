"""Real semantic retrieval via a Databricks embeddings serving endpoint.

Cosine similarity is computed in-process rather than through a managed Unity Catalog
Vector Search index: this corpus is a handful of chunks per offer, and an index adds
real setup (Delta table, sync pipeline, endpoint provisioning) and query latency for
no benefit at this scale. Revisit if a corpus grows large enough that holding all of
its chunk embeddings in memory stops being cheap (NOTES.md §2).

Import of the SDK is deferred to __init__, same reasoning as DatabricksFMGenerator: the
rest of the app runs without `databricks-sdk` installed or credentials configured.
"""
from __future__ import annotations

import math

from preboard.corpus import Chunk, ChunkSource
from preboard.retrieval import RetrievedChunk

# Empirically tested against data/*.md with 11 probe questions (6 grounded, 5 not) —
# see tests/test_embedding_retrieval_integration.py and NOTES.md §9. Scores did NOT
# separate cleanly: grounded ranged 0.576-0.757, ungrounded 0.392-0.602, overlapping in
# 0.58-0.62. 0.62 sits just above every ungrounded score in the sample (max 0.602), so
# the one grounded question that falls short (0.576) triggers a handoff rather than a
# wrong answer — the safe failure mode per invariant §1.4. Small sample; revisit with
# real usage data before trusting this past the demo.
EMBEDDING_CONFIDENCE_THRESHOLD = 0.62

DEFAULT_ENDPOINT = "databricks-gte-large-en"


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class EmbeddingRetriever:
    def __init__(self, source: ChunkSource, endpoint_name: str = DEFAULT_ENDPOINT):
        from databricks.sdk import WorkspaceClient  # noqa: PLC0415

        self._source = source
        self._endpoint_name = endpoint_name
        self._client = WorkspaceClient()
        # Chunk embeddings only change if the corpus changes, and this app's corpus is
        # static per run — compute once per offer, not once per question. Also spares
        # a Unity Catalog query (when UnityCatalogSource is wired in) per question.
        self._chunks_by_offer: dict[str, list[Chunk]] = {}
        self._embeddings_by_offer: dict[str, list[list[float]]] = {}

    def _embed(self, texts: list[str]) -> list[list[float]]:
        response = self._client.serving_endpoints.query(name=self._endpoint_name, input=texts)
        return [item.embedding for item in response.data]

    def _load_offer(self, offer_id: str) -> None:
        if offer_id in self._chunks_by_offer:
            return
        chunks = self._source.load(offer_id)
        self._chunks_by_offer[offer_id] = chunks
        self._embeddings_by_offer[offer_id] = self._embed([c.text for c in chunks]) if chunks else []

    def retrieve(self, offer_id: str, question: str) -> list[RetrievedChunk]:
        self._load_offer(offer_id)
        chunks = self._chunks_by_offer[offer_id]
        if not chunks:
            return []

        [q_embedding] = self._embed([question])
        chunk_embeddings = self._embeddings_by_offer[offer_id]

        results = [
            RetrievedChunk(chunk=chunk, score=_cosine(q_embedding, c_embedding))
            for chunk, c_embedding in zip(chunks, chunk_embeddings)
        ]
        results.sort(key=lambda r: r.score, reverse=True)
        return results
