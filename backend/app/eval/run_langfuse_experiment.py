"""Uploads the golden dataset to Langfuse and runs it as an offline
experiment, scored by the same two judges used in run_eval.py's local
runner -- this is the Langfuse half of Phase 4/5 that was deferred
pending API keys.

Requires the MCP server running (same as run_eval.py) and
LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY set.

Re-running this re-uploads dataset items each time (Langfuse dedupes
by dataset name, not by item content), so repeated runs will show
duplicate items in the Langfuse UI -- acceptable for this project's
scale, not worth building upsert logic for a handful of golden cases.

Usage: python -m app.eval.run_langfuse_experiment
"""

from __future__ import annotations

import os
import time

from dotenv import load_dotenv

load_dotenv()

# Eval-only budget override, same reasoning as run_eval.py: personas run
# on a cheaper model here, the real app still defaults to claude-opus-5.
# Must happen before app.graph.nodes is imported anywhere (including
# transitively via harness/build).
EVAL_PERSONA_MODEL = os.environ.get("EVAL_PERSONA_MODEL", "claude-sonnet-5")
os.environ["PITCH_TESTER_MODEL"] = EVAL_PERSONA_MODEL

from langfuse import Evaluation, get_client

from app.eval.golden_dataset import GOLDEN_CASES
from app.eval.harness import run_case
from app.eval.judges import judge_persona_consistency, judge_synthesis_quality

DATASET_NAME = "pitch-tester-golden"


def upload_dataset() -> None:
    client = get_client()
    client.create_dataset(name=DATASET_NAME)
    for case in GOLDEN_CASES:
        client.create_dataset_item(
            dataset_name=DATASET_NAME,
            input={
                "case_id": case["case_id"],
                "pitch": case["pitch"],
                "challenges": case["challenges"],
            },
            expected_output=case["expected_synthesis"],
            metadata={"archetype": case["archetype"]},
        )
    print(f"Uploaded {len(GOLDEN_CASES)} items to dataset '{DATASET_NAME}'")


def task(*, item, **kwargs):
    """Runs one dataset item through the real graph (same harness as
    run_eval.py's local runner) and returns the final state.
    """
    return run_case(item.input)


def persona_consistency_evaluator(*, input, output, expected_output, metadata, **kwargs):
    evaluations = []
    for persona in output.get("personas", []):
        thread = output.get("persona_threads", {}).get(persona["id"], [])
        if not thread:
            continue
        score = judge_persona_consistency(persona, thread)
        evaluations.append(
            Evaluation(
                name=f"incentive_consistency_{persona['id']}",
                value=score.incentive_consistency_score,
                comment=score.incentive_consistency_reasoning,
            )
        )
        if score.decision_earned_score is not None:
            evaluations.append(
                Evaluation(
                    name=f"decision_earned_{persona['id']}",
                    value=score.decision_earned_score,
                    comment=score.decision_earned_reasoning or "",
                )
            )
    return evaluations


def synthesis_quality_evaluator(*, input, output, expected_output, metadata, **kwargs):
    score = judge_synthesis_quality(output.get("synthesis"), expected_output)
    return [
        Evaluation(
            name="synthesis_agreement_match",
            value=score.agreement_match_score,
            comment=score.reasoning,
        ),
        Evaluation(
            name="synthesis_divergence_match", value=score.divergence_match_score
        ),
        Evaluation(name="synthesis_risk_match", value=score.risk_match_score),
    ]


def main() -> None:
    upload_dataset()
    dataset = get_client().get_dataset(DATASET_NAME)
    result = dataset.run_experiment(
        name="Offline golden-case eval",
        run_name=f"run-{int(time.time())}",
        task=task,
        evaluators=[persona_consistency_evaluator, synthesis_quality_evaluator],
    )
    print(result.format())


if __name__ == "__main__":
    main()
