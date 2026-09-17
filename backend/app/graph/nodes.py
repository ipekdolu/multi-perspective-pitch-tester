"""Node functions for the pitch-tester graph.

Phase 1 proved the graph shape with stub (non-LLM) logic. Phase 2 wired
in real Claude calls with incentive prompts hardcoded. Phase 3 removes
that hardcoding: persona_reaction and challenge_and_rebuttal now act as
MCP clients to the standalone persona-research server (mcp_server/) —
fetching each persona's incentive profile from the
persona_incentive_profile:// resource and grounding reactions in live
get_market_context search results, instead of a literal dict in this
file.
"""

from __future__ import annotations

import os

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.types import Command, Send, interrupt
from pydantic import BaseModel, Field
from typing import Literal

from app.graph.mcp_client import (
    fetch_market_context,
    fetch_persona_profile,
    log_challenge_outcome,
)
from app.graph.state import PitchTesterState
from app.llm_utils import invoke_structured

MODEL_NAME = os.environ.get("PITCH_TESTER_MODEL", "claude-opus-5")

# Structural routing info only (which personas this app fans out to) —
# not the incentive/eval data the doc calls out to move off hardcoding.
# That data now lives behind the MCP resource, fetched per branch below.
PERSONA_IDS = ["investor", "customer", "regulator"]


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


class SynthesisOutput(BaseModel):
    """Structured output for the synthesis node."""

    agreement: list[str] = Field(
        description="Real points where multiple personas actually "
        "converge, drawn from what they said — not generic positivity."
    )
    divergence: list[str] = Field(
        description="Real points where personas land in genuinely "
        "different places, naming which persona holds which position."
    )
    biggest_risk: str = Field(
        description="The single most significant risk raised anywhere "
        "in the transcript, in one or two sentences."
    )


def _persona_system_prompt(persona: dict, market_context: str | None = None) -> str:
    prompt = (
        f"{persona['system_prompt']}\n\n"
        f"Your incentive: {persona['incentive_statement']}\n\n"
        f"What you evaluate against: {'; '.join(persona['evaluation_criteria'])}\n\n"
        "Stay strictly within this incentive framing. Do not soften your "
        "position out of politeness — react the way this persona actually "
        "would, including genuine skepticism or disagreement."
    )
    if market_context:
        prompt += (
            "\n\nReal-world signal to ground your reaction in (weigh it, "
            f"don't just repeat it):\n{market_context}"
        )
    return prompt


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
        "personas": [],
        "persona_threads": {},
        "challenge_log": [],
        "round_count": 0,
        "human_approval": "pending",
        "synthesis": None,
    }


def route_to_personas(state: PitchTesterState) -> list[Send]:
    """Fan-out edge: dispatches one Send per persona to persona_reaction.

    Each Send carries only a persona id — persona_reaction fetches the
    actual profile from the MCP resource itself, so this routing step
    doesn't need to know anything about incentives or prompts.
    """
    return [
        Send("persona_reaction", {**state, "_persona_id": persona_id})
        for persona_id in PERSONA_IDS
    ]


def persona_reaction(state: PitchTesterState) -> dict:
    """Real persona reaction. One invocation per persona (via Send fan-out).

    Acts as an MCP client twice before generating a reaction: reads its
    own incentive profile from persona_incentive_profile://{id}, and
    calls get_market_context to ground the reaction in live signal
    instead of the model's own guesswork.
    """
    persona_id = state["_persona_id"]
    persona = fetch_persona_profile(persona_id)
    pitch_text = " ".join(state["pitch"]["claims"])
    market_context = fetch_market_context(
        topic=pitch_text, persona_role=persona["role"]
    )

    llm = ChatAnthropic(model=MODEL_NAME)
    response = llm.invoke(
        [
            SystemMessage(content=_persona_system_prompt(persona, market_context)),
            HumanMessage(
                content=f"Here is the pitch:\n\n{pitch_text}\n\n"
                "Give your first reaction in 2-4 sentences."
            ),
        ]
    )

    return {
        "personas": [persona],
        "persona_threads": {
            persona_id: [
                {"role": "persona", "content": _extract_text(response.content)}
            ]
        },
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
    decision: RebuttalDecision = invoke_structured(
        llm,
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

    # Server-side audit trail, independent of LangGraph's own checkpoint —
    # separate from the challenge_log field returned below.
    log_challenge_outcome(persona_id, challenge_text, outcome)

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
    """Real synthesis: reads the full transcript — every persona's
    initial reaction plus every challenge/rebuttal exchange, not just
    challenge_log outcomes — and extracts genuine agreement, genuine
    divergence, and the single biggest risk.

    The Phase 1-3 stub version derived this purely from challenge_log,
    which structurally can't see anything from the personas' initial
    reactions (e.g. shared enthusiasm or shared concern that was never
    challenged). Phase 4's eval surfaced that as a permanently-floored
    synthesis_quality score against the golden references — this
    replaces it with what the architecture doc always described: a
    node that reads the full transcript.
    """
    transcript_parts = []
    for persona in state["personas"]:
        thread = state["persona_threads"].get(persona["id"], [])
        thread_text = "\n".join(f"  [{m['role']}] {m['content']}" for m in thread)
        transcript_parts.append(
            f"=== {persona['name']} ({persona['role']}) ===\n{thread_text}"
        )
    transcript = "\n\n".join(transcript_parts)

    llm = ChatAnthropic(model=MODEL_NAME).with_structured_output(SynthesisOutput)
    result: SynthesisOutput = invoke_structured(
        llm,
        [
            SystemMessage(
                content=(
                    "You are synthesizing a multi-perspective pitch review. "
                    "Read the full transcript below — every persona's "
                    "initial reaction and every challenge/rebuttal exchange "
                    "— and extract: (1) real agreement across personas "
                    "(only things multiple personas actually converge on, "
                    "not vague positivity), (2) real divergence (where "
                    "personas genuinely land in different places, and "
                    "why), and (3) the single biggest risk raised anywhere "
                    "in the transcript. Be concrete and specific, grounded "
                    "in what was actually said."
                )
            ),
            HumanMessage(content=transcript),
        ]
    )

    return {"synthesis": result.model_dump()}
