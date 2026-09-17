"""LLM-as-judge scorers for the eval suite.

Judge model defaults to claude-sonnet-5, not the claude-opus-5 the
personas themselves use — a judge scoring already-generated transcripts
is exactly the "cheaper secondary model" role (grading, not generating),
so there's no reason to pay Opus rates for it. Override via
EVAL_JUDGE_MODEL if you want otherwise.
"""

from __future__ import annotations

import os
from typing import Literal

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.llm_utils import invoke_structured

JUDGE_MODEL = os.environ.get("EVAL_JUDGE_MODEL", "claude-sonnet-5")

Score = Literal[1, 2, 3, 4, 5]


class PersonaConsistencyScore(BaseModel):
    """Judge 1: reads one persona's full thread in isolation."""

    incentive_consistency_score: Score = Field(
        description="1 (broke character / gave generic assistant advice) "
        "to 5 (every turn is clearly argued from the stated incentive "
        "alone, no drift toward being helpful/agreeable for its own sake)."
    )
    incentive_consistency_reasoning: str
    decision_earned_score: Score | None = Field(
        default=None,
        description="Only set if the thread contains at least one "
        "challenge/rebuttal. 1 (hold/concede looks reflexive — same "
        "regardless of challenge strength) to 5 (the hold/concede "
        "decision is clearly proportionate to how strong the specific "
        "challenge actually was).",
    )
    decision_earned_reasoning: str | None = None


class SynthesisQualityScore(BaseModel):
    """Judge 2: compares actual synthesis against the golden reference."""

    agreement_match_score: Score = Field(
        description="1 (misses or fabricates agreement points vs. the "
        "reference) to 5 (captures the same real agreement the "
        "reference identifies)."
    )
    divergence_match_score: Score = Field(
        description="Same scale, for whether divergence points match "
        "the reference's substance."
    )
    risk_match_score: Score = Field(
        description="Same scale, for whether the identified biggest "
        "risk matches the reference's core concern (doesn't need "
        "identical wording, needs the same underlying issue)."
    )
    reasoning: str


def judge_persona_consistency(
    persona: dict, thread: list[dict]
) -> PersonaConsistencyScore:
    thread_text = "\n\n".join(f"[{m['role']}] {m['content']}" for m in thread)
    llm = ChatAnthropic(model=JUDGE_MODEL).with_structured_output(
        PersonaConsistencyScore
    )
    return invoke_structured(
        llm,
        [
            SystemMessage(
                content=(
                    "You are grading a transcript from an AI persona "
                    "roleplaying agent, not participating in the "
                    "conversation. Be a strict, skeptical grader — do "
                    "not give high scores by default."
                )
            ),
            HumanMessage(
                content=(
                    f"Persona: {persona['name']} ({persona['role']})\n"
                    f"Stated incentive: {persona['incentive_statement']}\n\n"
                    f"Full thread:\n{thread_text}\n\n"
                    "Score this persona's consistency per the rubric."
                )
            ),
        ]
    )


def judge_synthesis_quality(
    actual_synthesis: dict, expected_synthesis: dict
) -> SynthesisQualityScore:
    llm = ChatAnthropic(model=JUDGE_MODEL).with_structured_output(
        SynthesisQualityScore
    )
    return invoke_structured(
        llm,
        [
            SystemMessage(
                content=(
                    "You are grading a synthesis output against a "
                    "reference synthesis written by a human. Compare "
                    "substance, not wording — different phrasing of the "
                    "same underlying point should score well. Be a "
                    "strict, skeptical grader."
                )
            ),
            HumanMessage(
                content=(
                    f"Reference (golden) synthesis:\n{expected_synthesis}\n\n"
                    f"Actual synthesis to grade:\n{actual_synthesis}\n\n"
                    "Score the actual synthesis against the reference "
                    "per the rubric."
                )
            ),
        ]
    )
