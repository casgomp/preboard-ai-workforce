"""Answer generation.

NOTES.md invariant §1.3: no answer without a retrieved chunk. Every `Generator` here
takes the retrieved chunks as required context — there is no path that lets a caller
ask for an answer without at least one. Multiple chunks (PR4) let one answer draw on
several sections of the offer packet instead of only ever the single best match.
"""
from __future__ import annotations

from typing import Protocol

from preboard.corpus import Chunk


class Generator(Protocol):
    def generate(self, question: str, chunks: list[Chunk]) -> str: ...


class StubGenerator:
    """Deterministic, no network — used for local dev and tests."""

    def generate(self, question: str, chunks: list[Chunk]) -> str:
        return "\n\n".join(chunk.text.strip() for chunk in chunks)


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

    def generate(self, question: str, chunks: list[Chunk]) -> str:
        from databricks.sdk.service.serving import ChatMessage, ChatMessageRole  # noqa: PLC0415

        excerpts = "\n\n".join(f"Excerpt — {chunk.section}:\n{chunk.text}" for chunk in chunks)
        prompt = (
            "You are answering a new hire's question about their offer packet, before "
            "their first day. Write a direct, natural answer in your own words — don't "
            "just quote or list the excerpts verbatim. Synthesize across ALL the "
            "excerpts below if more than one is relevant to the question. Use ONLY "
            "information in the excerpts; if they don't fully answer the question, say "
            "plainly what's missing rather than guessing.\n\n"
            f"{excerpts}\n\n"
            f"Question: {question}"
        )
        response = self._client.serving_endpoints.query(
            name=self._endpoint_name,
            messages=[ChatMessage(role=ChatMessageRole.USER, content=prompt)],
        )
        return response.choices[0].message.content
