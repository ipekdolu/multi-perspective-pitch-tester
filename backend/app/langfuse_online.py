"""Langfuse tracing + online sampled judge scoring for live API runs.

Degrades to a no-op when LANGFUSE_PUBLIC_KEY isn't set -- Langfuse is
observability, not a hard dependency for the app to run.

Only Judge 1 (persona consistency) runs online. Judge 2 (synthesis
quality) is defined as a reference-comparison against a golden
synthesis (see eval/judges.py) -- live user pitches have no golden
reference to compare against, so it only makes sense in the offline
experiment against golden_dataset.py (eval/run_langfuse_experiment.py).
Running it online with no reference would mean inventing a different,
undocumented judge -- out of scope for what the doc specifies.
"""

from __future__ import annotations

import os
import random

LANGFUSE_ENABLED = bool(os.environ.get("LANGFUSE_PUBLIC_KEY"))
SAMPLE_RATE = float(os.environ.get("LANGFUSE_ONLINE_SAMPLE_RATE", "0.2"))


def get_callbacks(trace_id: str | None) -> list:
    """Callbacks list for a graph.invoke config. Empty list if Langfuse
    isn't configured or no trace_id was made, so callers never need to
    branch on whether Langfuse is enabled.
    """
    if not LANGFUSE_ENABLED or trace_id is None:
        return []
    from langfuse.langchain import CallbackHandler

    return [CallbackHandler(trace_context={"trace_id": trace_id})]


def make_trace_id(thread_id: str) -> str | None:
    """Deterministic trace id seeded from thread_id, so every HTTP call
    that resumes the same run (challenge/done/approve/reject) attaches
    to the same Langfuse trace instead of fragmenting into one trace
    per request.
    """
    if not LANGFUSE_ENABLED:
        return None
    from langfuse import get_client

    return get_client().create_trace_id(seed=thread_id)


def maybe_score_run(trace_id: str | None, final_state: dict) -> None:
    """Sampled online scoring: with probability SAMPLE_RATE, run the
    persona-consistency judge against this completed live run's
    persona threads and attach the scores to its Langfuse trace.
    """
    if not LANGFUSE_ENABLED or trace_id is None:
        return
    if not final_state.get("synthesis"):
        return  # only score completed runs
    if random.random() >= SAMPLE_RATE:
        return

    from langfuse import get_client

    from app.eval.judges import judge_persona_consistency

    client = get_client()
    for persona in final_state.get("personas", []):
        thread = final_state.get("persona_threads", {}).get(persona["id"], [])
        if not thread:
            continue
        score = judge_persona_consistency(persona, thread)
        client.create_score(
            trace_id=trace_id,
            name=f"persona_consistency_incentive_{persona['id']}",
            value=score.incentive_consistency_score,
            data_type="NUMERIC",
            comment=score.incentive_consistency_reasoning,
        )
        if score.decision_earned_score is not None:
            client.create_score(
                trace_id=trace_id,
                name=f"persona_consistency_decision_earned_{persona['id']}",
                value=score.decision_earned_score,
                data_type="NUMERIC",
                comment=score.decision_earned_reasoning or "",
            )
