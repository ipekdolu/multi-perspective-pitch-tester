"""Non-interactive harness: runs one golden-dataset case through the
real compiled graph end to end, driving both interrupt() points with
the case's scripted challenges instead of a human at the keyboard.
"""

from __future__ import annotations

import uuid

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from app.graph.build import build_graph_definition


def run_case(case: dict) -> dict:
    """Runs `case` through the graph and returns the final state values
    (persona_threads, challenge_log, synthesis, ...).

    Uses an in-memory checkpointer rather than the SQLite one build.py
    uses for the CLI: eval runs are one-shot within a single process,
    so there's no need for cross-process resume or a file left on disk
    per case.
    """
    graph = build_graph_definition().compile(checkpointer=MemorySaver())
    config = {
        "configurable": {"thread_id": f"eval-{case['case_id']}-{uuid.uuid4().hex[:8]}"}
    }

    graph.invoke({"raw_pitch": case["pitch"]}, config=config)

    for challenge in case["challenges"]:
        graph.invoke(
            Command(
                resume={
                    "action": "challenge",
                    "persona_id": challenge["persona_id"],
                    "text": challenge["challenge_text"],
                }
            ),
            config=config,
        )

    graph.invoke(Command(resume={"action": "done"}), config=config)
    graph.invoke(Command(resume={"decision": "approved"}), config=config)

    return graph.get_state(config).values
