"""Node functions for the pitch-tester graph.

Phase 1 proved the graph shape with stub (non-LLM) logic. Phase 2 replaces
the two persona-facing nodes (persona_reaction, challenge_and_rebuttal)
with real Claude calls; intake and synthesis stay as they were — the doc
only calls for real personas in this phase.
"""

from __future__ import annotations

import os

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END
from langgraph.types import Command, Send, interrupt
from pydantic import BaseModel, Field
from typing import Literal

from app.graph.state import PitchTesterState

MODEL_NAME = os.environ.get("PITCH_TESTER_MODEL", "claude-opus-5")

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


class RebuttalDecision(BaseModel):
    """Structured output for a persona's hold/concede decision.

    Forcing this through structured output (rather than parsing free
    text) is what makes `outcome` reliable enough to double as the
    eval golden-trace format called out later in the doc.
    """

    outcome: Literal["held", "conceded"] = Field(
        description="'held' if the persona's original point still stands "
        "against this challenge, 'conceded' if the challenge genuinely "
        "changes their position."
    )
    response_text: str = Field(
        description="The persona's in-character rebuttal or concession, "
        "2-4 sentences, staying strictly within their stated incentive."
    )


def _persona_system_prompt(persona: dict) -> str:
    return (
        f"{persona['system_prompt']}\n\n"
        f"Your incentive: {persona['incentive_statement']}\n\n"
        "Stay strictly within this incentive framing. Do not soften your "
        "position out of politeness — react the way this persona actually "
        "would, including genuine skepticism or disagreement."
    )


def _extract_text(content) -> str:
    """Claude Opus 5 runs extended thinking by default, so message content
    comes back as a list of blocks (a `thinking` block plus one or more
    `text` blocks) rather than a plain string. Pull out just the text.
    """
    if isinstance(content, str):
        return content
    return "".join(
        block.get("text", "")
        for block in content
        if isinstance(block, dict) and block.get("type") == "text"
    )


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
    """Real persona reaction. One invocation per persona (via Send fan-out).

    Reads `_active_persona`, injected by route_to_personas — not part of
    the permanent schema, just the payload for this one Send branch.
    """
    persona = state["_active_persona"]
    persona_id = persona["id"]

    llm = ChatAnthropic(model=MODEL_NAME)
    pitch_text = " ".join(state["pitch"]["claims"])
    response = llm.invoke(
        [
            SystemMessage(content=_persona_system_prompt(persona)),
            HumanMessage(
                content=f"Here is the pitch:\n\n{pitch_text}\n\n"
                "Give your first reaction in 2-4 sentences."
            ),
        ]
    )

    return {
        "persona_threads": {
            persona_id: [
                {"role": "persona", "content": _extract_text(response.content)}
            ]
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
    """Real challenge/rebuttal: replays the persona's full thread (its
    original reaction plus any prior challenge rounds) as message
    history, then asks the model to genuinely decide hold vs. concede
    against this specific challenge — via structured output, not a
    hardcoded lookup.
    """
    persona_id = state["pending_challenge_persona_id"]
    challenge_text = state["pending_challenge_text"]
    persona = next(p for p in state["personas"] if p["id"] == persona_id)

    history = []
    for msg in state["persona_threads"].get(persona_id, []):
        if msg["role"] == "persona":
            history.append(AIMessage(content=msg["content"]))
        else:
            history.append(HumanMessage(content=msg["content"]))

    llm = ChatAnthropic(model=MODEL_NAME).with_structured_output(RebuttalDecision)
    decision: RebuttalDecision = llm.invoke(
        [
            SystemMessage(
                content=_persona_system_prompt(persona)
                + "\n\nYou are being challenged on your prior reaction. Decide "
                "honestly: does this specific challenge change your position "
                "('conceded'), or does your original point still stand "
                "('held')? Do not concede reflexively to be agreeable, and "
                "do not hold reflexively out of stubbornness — the decision "
                "must be earned by the strength of the challenge."
            ),
            *history,
            HumanMessage(content=challenge_text),
        ]
    )
    outcome = decision.outcome
    response_text = decision.response_text

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
