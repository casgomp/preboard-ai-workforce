"""HR-facing section drafting (PLAN_PR15 B6).

This is the one place in the product that generates text without a retrieved
chunk. NOTES.md invariant §1.3 ("no answer without a retrieved chunk") governs
candidate-facing answers via `QA.ask`/`Generator.generate` — both require
`chunks: list[Chunk]` as a real argument, not an optional one, so there is no path
from a candidate's question to invented text. `draft_section` is deliberately a
separate function, not a `Generator` implementation and never called from
`QA.ask`: a gap row has nothing to retrieve, which is the whole reason it's a gap.
Its output never reaches a candidate — it's a starting point for a human at the
named department to review, edit, and decide whether to publish, always returned
labelled as a draft. See NOTES.md §1 for the amended invariant text.
"""
from __future__ import annotations


def draft_section(question: str, department: str, endpoint_name: str) -> str:
    from databricks.sdk import WorkspaceClient  # noqa: PLC0415
    from databricks.sdk.service.serving import (  # noqa: PLC0415
        ChatMessage,
        ChatMessageRole,
    )

    prompt = (
        f"You are drafting a short handbook paragraph for the {department} team's "
        "new-hire documentation, to fill a real gap: a candidate asked a question "
        "that nothing in the current documents answers.\n\n"
        f"Question: {question}\n\n"
        "Write a brief, factual paragraph in the voice of a company handbook that "
        "WOULD answer this question. Use placeholder brackets — [amount], "
        "[number of days], [policy detail] — for anything you cannot know without "
        "real company information. Never invent a specific number, date, name, "
        "contact, or policy. This is a first draft for a human reviewer at "
        f"{department} to edit before anyone sees it, not a finished answer."
    )
    client = WorkspaceClient()
    response = client.serving_endpoints.query(
        name=endpoint_name,
        messages=[ChatMessage(role=ChatMessageRole.USER, content=prompt)],
    )
    return response.choices[0].message.content
