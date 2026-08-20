"""Answer generation.

NOTES.md invariant §1.3: no answer without a retrieved chunk. Every `Generator` here
takes the retrieved chunk as required context — there is no path that lets a caller ask
for an answer without one.
"""
from __future__ import annotations

from typing import Protocol

from preboard.corpus import Chunk


class Generator(Protocol):
    def generate(self, question: str, chunk: Chunk) -> str: ...


class StubGenerator:
    """Deterministic, no network — used for local dev and tests."""

    def generate(self, question: str, chunk: Chunk) -> str:
        return chunk.text.strip()


class DatabricksFMGenerator:
    """Calls a Databricks Foundation Model serving endpoint.

    Import of the SDK is deferred to __init__ so the rest of the app runs without
    `databricks-sdk` installed or any Databricks credentials configured — only code
    paths that actually hit a real endpoint need either.
    """

    def __init__(self, endpoint_name: str):
        from databricks.sdk import WorkspaceClient  # noqa: PLC0415

        self._endpoint_name = endpoint_name
        self._client = WorkspaceClient()

    def generate(self, question: str, chunk: Chunk) -> str:
        from databricks.sdk.service.serving import ChatMessage, ChatMessageRole  # noqa: PLC0415

        prompt = (
            "Answer the candidate's question using ONLY the excerpt below. "
            "If the excerpt doesn't contain the answer, say so plainly.\n\n"
            f"Excerpt ({chunk.section}):\n{chunk.text}\n\n"
            f"Question: {question}"
        )
        response = self._client.serving_endpoints.query(
            name=self._endpoint_name,
            messages=[ChatMessage(role=ChatMessageRole.USER, content=prompt)],
        )
        return response.choices[0].message.content
