"""Answer generation.

NOTES.md invariant §1.3: no answer without a retrieved chunk. Every `Generator` here
takes the retrieved chunks as required context — there is no path that lets a caller
ask for an answer without at least one. Multiple chunks let one answer draw on
several sections of the offer packet.

`date_context` is an optional plain-language line QA computes from preboard.offers.
It resolves relative phrasing such as "about a week before your start date" into
concrete timing when appropriate.

`language` (PLAN_PR15 B1/D1) is keyword-only with a default so a stale two-argument
fake fails loudly at the call site rather than silently binding the wrong thing
(R1 — this exact bug already happened once, PR6). The corpus and citations stay
English (NOTES.md §2's "German-first corpus" deferred item still holds, TRIGGER
unfired) — only the answer's language changes, so nothing in the §9 retrieval
threshold calibration (measured against English embeddings) is affected.
"""
from __future__ import annotations

from typing import Protocol

from preboard.corpus import Chunk


class Generator(Protocol):
    def generate(
        self,
        question: str,
        chunks: list[Chunk],
        date_context: str | None = None,
        *,
        language: str | None = None,
    ) -> str: ...


class StubGenerator:
    """Deterministic, no-network generator used for local development and tests.

    The stub intentionally returns retrieved source text directly rather than
    pretending to perform AI generation. The Databricks generator handles
    natural-language synthesis when real Databricks credentials are configured.
    `language` is accepted (protocol conformance) but has no effect — there's no
    translation to do when the answer is just echoed source text.
    """

    def generate(
        self,
        question: str,
        chunks: list[Chunk],
        date_context: str | None = None,
        *,
        language: str | None = None,
    ) -> str:
        del language
        return "\n\n".join(chunk.text.strip() for chunk in chunks)


class DatabricksFMGenerator:
    """Calls a Databricks Foundation Model serving endpoint.

    Import of the SDK is deferred to __init__ so the rest of the app runs without
    `databricks-sdk` installed or Databricks credentials configured. Only code paths
    that actually hit a real endpoint require either.
    """

    def __init__(self, endpoint_name: str):
        from databricks.sdk import WorkspaceClient  # noqa: PLC0415

        self._endpoint_name = endpoint_name
        self._client = WorkspaceClient()

    # PLAN_PR15 D1: full names for the prompt instruction, keyed by the short code
    # the frontend toggle sends. Only languages the toggle actually offers — an
    # unrecognized code falls back to no instruction (answers in English, today's
    # behavior) rather than guessing at a name to hand the model.
    _LANGUAGE_NAMES = {"de": "German"}

    def generate(
        self,
        question: str,
        chunks: list[Chunk],
        date_context: str | None = None,
        *,
        language: str | None = None,
    ) -> str:
        from databricks.sdk.service.serving import (  # noqa: PLC0415
            ChatMessage,
            ChatMessageRole,
        )

        excerpts = "\n\n".join(
            f"Excerpt — {chunk.section}:\n{chunk.text}" for chunk in chunks
        )

        date_line = f"{date_context}\n\n" if date_context else ""

        language_name = self._LANGUAGE_NAMES.get(language or "")
        language_line = (
            f"Write your answer in {language_name}. The excerpts below are in English — "
            "use them as source material, but do not quote them in English and do not "
            "translate any document title or proper noun that appears in them.\n\n"
            if language_name
            else ""
        )

        prompt = (
            "You are answering a new hire's question about their offer packet, "
            "before their first day.\n\n"

            "Answer the question directly and concisely. Put the most important "
            "answer first.\n\n"

            "Do not repeat information just because it appears in multiple "
            "excerpts. If multiple excerpts contain overlapping information, "
            "combine them into one clear statement.\n\n"

            "Use additional excerpts only when they add information needed to "
            "answer the question.\n\n"

            "Use ONLY information contained in the excerpts below. If the "
            "excerpts do not contain enough information to answer the question, "
            "say plainly what is missing rather than guessing.\n\n"

            "Never invent salary, compensation, dates, names, policies, contact "
            "information, benefits, or other facts.\n\n"

            "Do not simply copy or list the excerpts verbatim. Write a clear, "
            "natural answer in your own words.\n\n"

            "If a date line is provided and an excerpt describes timing relative "
            "to the start date, such as 'about a week before your start date', "
            "resolve it to a concrete date or number of days from today when "
            "appropriate.\n\n"

            "Keep the answer focused on exactly what the candidate asked. "
            "Do not add unrelated information from other excerpts.\n\n"

            f"{language_line}"
            f"{date_line}"
            f"{excerpts}\n\n"
            f"Question: {question}"
        )

        response = self._client.serving_endpoints.query(
            name=self._endpoint_name,
            messages=[
                ChatMessage(
                    role=ChatMessageRole.USER,
                    content=prompt,
                )
            ],
        )

        return response.choices[0].message.content
