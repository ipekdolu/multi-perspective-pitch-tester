"""State schema for the pitch-tester LangGraph app.

This is the single object every node reads from and writes back into.
LangGraph merges each node's returned dict into this state using the
reducers declared via `Annotated` below — plain fields get overwritten,
`Annotated[..., operator.add]` fields get appended/merged instead.
"""

from __future__ import annotations

import operator
from typing import Annotated, Literal, TypedDict


class PersonaConfig(TypedDict):
    id: str
    name: str
    role: str
    incentive_statement: str
    evaluation_criteria: list[str]
    system_prompt: str


class Message(TypedDict):
    role: Literal["persona", "user"]
    content: str


class ChallengeLogEntry(TypedDict):
    persona_id: str
    challenge_text: str
    response_text: str
    outcome: Literal["held", "conceded"]


class StructuredPitch(TypedDict):
    claims: list[str]
    target_market: str
    ask: str


class Synthesis(TypedDict):
    agreement: list[str]
    divergence: list[str]
    biggest_risk: str


def merge_threads(
    left: dict[str, list[Message]], right: dict[str, list[Message]]
) -> dict[str, list[Message]]:
    """Reducer for persona_threads: append new messages per persona id
    instead of one node's update wiping out another's thread.
    """
    merged = {k: list(v) for k, v in left.items()}
    for persona_id, new_messages in right.items():
        merged.setdefault(persona_id, [])
        merged[persona_id] = merged[persona_id] + new_messages
    return merged


class PitchTesterState(TypedDict):
    # Raw text the user submits at invocation time; intake() consumes this
    # and produces the structured `pitch` field below.
    raw_pitch: str

    pitch: StructuredPitch
    # Phase 3: each persona_reaction branch fetches its own profile from
    # the MCP resource and contributes it here — operator.add because all
    # three parallel Send() branches write to this key in the same
    # superstep; a plain (unreduced) field would conflict.
    personas: Annotated[list[PersonaConfig], operator.add]
    persona_threads: Annotated[dict[str, list[Message]], merge_threads]
    challenge_log: Annotated[list[ChallengeLogEntry], operator.add]
    round_count: int
    human_approval: Literal["pending", "approved", "rejected"]
    synthesis: Synthesis | None

    # Working fields used only during a single challenge/rebuttal pass —
    # not part of the doc's minimum schema, but needed to route a
    # challenge to the correct persona at node 4.
    pending_challenge_persona_id: str | None
    pending_challenge_text: str | None

    # Set only on the per-branch copy of state a Send() carries into
    # persona_reaction; absent on the "main" state everywhere else. Just
    # a routing id — persona_reaction fetches the actual profile from
    # the MCP resource, it doesn't come from the graph itself.
    _persona_id: str
