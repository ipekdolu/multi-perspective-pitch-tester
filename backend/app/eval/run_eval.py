"""Offline eval runner: runs every golden case through the real graph,
scores it with both judges, and prints/saves a results summary.

Requires the MCP server (mcp_server/server.py) running — persona_reaction
is an MCP client, same as any other graph run.

Personas run on EVAL_PERSONA_MODEL (default claude-sonnet-5) rather than
the app's real default (claude-opus-5, set via PITCH_TESTER_MODEL) — an
eval-only override to fit an API budget, not a change to what the real
app uses. nodes.py reads its model name from PITCH_TESTER_MODEL at
import time, so this must be set before app.graph.nodes is imported
anywhere in the process (including transitively via harness/build).

Usage: python -m app.eval.run_eval
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

EVAL_PERSONA_MODEL = os.environ.get("EVAL_PERSONA_MODEL", "claude-sonnet-5")
os.environ["PITCH_TESTER_MODEL"] = EVAL_PERSONA_MODEL

from app.eval.golden_dataset import GOLDEN_CASES
from app.eval.harness import run_case
from app.eval.judges import judge_persona_consistency, judge_synthesis_quality

RESULTS_PATH = Path(__file__).parent / "eval_results.json"


def run_all() -> list[dict]:
    results = []

    for case in GOLDEN_CASES:
        print(f"\n=== {case['case_id']} ({case['archetype']}) ===")
        final_state = run_case(case)

        persona_scores = {}
        for persona in final_state["personas"]:
            thread = final_state["persona_threads"].get(persona["id"], [])
            score = judge_persona_consistency(persona, thread)
            persona_scores[persona["id"]] = score.model_dump()
            print(
                f"  persona_consistency[{persona['id']}]: "
                f"incentive={score.incentive_consistency_score} "
                f"decision_earned={score.decision_earned_score}"
            )

        synthesis_score = judge_synthesis_quality(
            final_state["synthesis"], case["expected_synthesis"]
        )
        print(
            f"  synthesis_quality: agreement={synthesis_score.agreement_match_score} "
            f"divergence={synthesis_score.divergence_match_score} "
            f"risk={synthesis_score.risk_match_score}"
        )

        results.append(
            {
                "case_id": case["case_id"],
                "archetype": case["archetype"],
                "challenge_log": final_state["challenge_log"],
                "synthesis": final_state["synthesis"],
                "persona_consistency_scores": persona_scores,
                "synthesis_quality_score": synthesis_score.model_dump(),
            }
        )

    return results


def summarize(results: list[dict]) -> None:
    all_scores = []
    for r in results:
        for s in r["persona_consistency_scores"].values():
            all_scores.append(s["incentive_consistency_score"])
            if s["decision_earned_score"] is not None:
                all_scores.append(s["decision_earned_score"])
        sq = r["synthesis_quality_score"]
        all_scores += [
            sq["agreement_match_score"],
            sq["divergence_match_score"],
            sq["risk_match_score"],
        ]

    print("\n=== summary ===")
    print(f"total scores collected: {len(all_scores)}")
    print(f"min={min(all_scores)} max={max(all_scores)} "
          f"distinct_values={sorted(set(all_scores))}")
    if len(set(all_scores)) == 1:
        print("WARNING: every score is identical — judges are not differentiating.")
    else:
        print("Scores are differentiated across cases (not uniform).")


if __name__ == "__main__":
    print(f"Running personas on {EVAL_PERSONA_MODEL} (eval-only override)")
    results = run_all()
    RESULTS_PATH.write_text(json.dumps(results, indent=2))
    print(f"\nWrote results to {RESULTS_PATH}")
    summarize(results)
