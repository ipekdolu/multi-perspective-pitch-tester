"""Node functions for the pitch-tester graph.

Phase 1: every node uses stub logic (no LLM calls). The point of this
phase is to prove the graph SHAPE and the interrupt/resume mechanism,
not persona quality — that's Phase 2.
"""

from __future__ import annotations

from langgraph.graph import END
from langgraph.types import Command, Send, interrupt

from app.graph.state import PitchTesterState

STUB_PERSONAS = [
    {
        "id": "investor",
        "name": "Investor",
        "role": "investor",
        "incentive_statement": "Wants outsized financial return within a fund's time horizon; skeptical of unproven markets.",
        "system_prompt": "You are an investor persona. React from a pure ROI/risk lens.",
    },
    {
        "id": "customer",
        "name": "Customer",
        "role": "customer",
        "incentive_statement": "Wants a real problem solved with minimal switching cost; skeptical of unproven products.",
        "system_prompt": "You are a customer persona. React from a pure usefulness/adoption-friction lens.",
    },
    {
        "id": "regulator",
        "name": "Regulator",
        "role": "regulator",
        "incentive_statement": "Wants compliance and harm prevention; skeptical of unvetted claims.",
        "system_prompt": "You are a regulator persona. React from a pure compliance/risk-to-public lens.",
    },
]

STUB_REACTIONS = {
    "investor": "Market size claim is unverified - what's the comparable exit multiple?",
    "customer": "This solves a real pain point, but the switching cost from our current tool looks high.",
    "regulator": "The data-handling claim needs a named legal basis before I'd sign off.",
}

STUB_REBUTTALS = {
    "investor": "held",
    "customer": "conceded",
    "regulator": "held",
}


def intake(state: PitchTesterState) -> dict:
    """Stub intake: naively splits the raw pitch into a structured form.

    Real version (Phase 2+) would use an LLM extraction call here.
    """
    raw = state["raw_pitch"]
    return {
        "pitch": {
            "claims": [raw],
            "target_market": "unspecified (stub)",
            "ask": "unspecified (stub)",
        },
        "personas": STUB_PERSONAS,
        "persona_threads": {},
        "challenge_log": [],
        "round_count": 0,
        "human_approval": "pending",
        "synthesis": None,
    }


def route_to_personas(state: PitchTesterState) -> list[Send]:
    """Fan-out edge: dispatches one Send per persona to persona_reaction.

    This is the LangGraph `Send` API referenced in the design doc —
    each Send carries its own copy of the persona config so the
    parallel branches don't need to share mutable state mid-flight.
    """
    return [
        Send("persona_reaction", {**state, "_active_persona": persona})
        for persona in state["personas"]
    ]


def persona_reaction(state: PitchTesterState) -> dict:
    """Stub persona reaction. One invocation per persona (via Send fan-out).

    Reads `_active_persona`, injected by route_to_personas — not part of
    the permanent schema, just the payload for this one Send branch.
    """
    persona = state["_active_persona"]
    persona_id = persona["id"]
    reaction_text = STUB_REACTIONS[persona_id]
    return {
        "persona_threads": {
            persona_id: [{"role": "persona", "content": reaction_text}]
        }
    }


def present_findings(state: PitchTesterState) -> Command:
    """Join point after the parallel fan-out. Interrupts to await either
    a challenge (persona_id + text) or a "done" signal from the user.

    Resuming this interrupt requires passing a dict shaped like:
      {"action": "challenge", "persona_id": "investor", "text": "..."}
    or:
      {"action": "done"}
    """
    payload = interrupt(
        {
            "type": "present_findings",
            "persona_threads": state["persona_threads"],
        }
    )

    if payload["action"] == "challenge":
        return Command(
            goto="challenge_and_rebuttal",
            update={
                "pending_challenge_persona_id": payload["persona_id"],
                "pending_challenge_text": payload["text"],
            },
        )
    return Command(goto="human_approval_gate")


def challenge_and_rebuttal(state: PitchTesterState) -> dict:
    """Stub challenge/rebuttal: routes the challenge to the target
    persona's own thread and appends a canned hold/concede response.

    Real version (Phase 2+) replaces STUB_REBUTTALS with an LLM call
    that reads the persona's full thread (including this challenge)
    before deciding hold vs. concede.
    """
    persona_id = state["pending_challenge_persona_id"]
    challenge_text = state["pending_challenge_text"]
    outcome = STUB_REBUTTALS[persona_id]
    response_text = (
        f"[stub {outcome}] responding to: {challenge_text}"
    )

    return {
        "persona_threads": {
            persona_id: [
                {"role": "user", "content": challenge_text},
                {"role": "persona", "content": response_text},
            ]
        },
        "challenge_log": [
            {
                "persona_id": persona_id,
                "challenge_text": challenge_text,
                "response_text": response_text,
                "outcome": outcome,
            }
        ],
        "round_count": state["round_count"] + 1,
        "pending_challenge_persona_id": None,
        "pending_challenge_text": None,
    }


def human_approval_gate(state: PitchTesterState) -> Command:
    """Second interrupt: approve to finalize, or reject to loop back
    for another round of challenges.

    Resume payload shape: {"decision": "approved"} or {"decision": "rejected"}.
    """
    payload = interrupt(
        {
            "type": "human_approval_gate",
            "challenge_log": state["challenge_log"],
        }
    )
    decision = payload["decision"]
    if decision == "approved":
        return Command(goto="synthesis", update={"human_approval": "approved"})
    return Command(
        goto="present_findings", update={"human_approval": "rejected"}
    )


def synthesis(state: PitchTesterState) -> dict:
    """Stub synthesis: derives agreement/divergence/risk directly from
    the challenge log rather than calling an LLM.
    """
    held = [c for c in state["challenge_log"] if c["outcome"] == "held"]
    conceded = [c for c in state["challenge_log"] if c["outcome"] == "conceded"]
    return {
        "synthesis": {
            "agreement": [f"{c['persona_id']} conceded" for c in conceded],
            "divergence": [f"{c['persona_id']} held" for c in held],
            "biggest_risk": held[0]["challenge_text"] if held else "none identified (stub)",
        }
    }
