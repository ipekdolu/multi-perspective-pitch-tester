"""Wires the seven-node graph together with a SQLite checkpointer.

Checkpointer choice (Phase 1): SQLite, not Postgres/Supabase. This phase's
job is to prove interrupt/resume works at all — SQLite needs zero external
setup, so nothing but the graph itself is on the hook for the milestone.
Swapping in `PostgresSaver` later is a one-line change: both implement the
same `BaseCheckpointSaver` interface, so no node code changes.
"""

from __future__ import annotations

from contextlib import contextmanager

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from app.graph.nodes import (
    challenge_and_rebuttal,
    human_approval_gate,
    intake,
    persona_reaction,
    present_findings,
    route_to_personas,
    synthesis,
)
from app.graph.state import PitchTesterState

DEFAULT_DB_PATH = "pitch_tester_checkpoints.sqlite"


def build_graph_definition() -> StateGraph:
    graph = StateGraph(PitchTesterState)

    graph.add_node("intake", intake)
    graph.add_node("persona_reaction", persona_reaction)
    graph.add_node("present_findings", present_findings)
    graph.add_node("challenge_and_rebuttal", challenge_and_rebuttal)
    graph.add_node("human_approval_gate", human_approval_gate)
    graph.add_node("synthesis", synthesis)

    graph.add_edge(START, "intake")
    # Fan-out: intake -> N parallel persona_reaction branches via Send
    graph.add_conditional_edges("intake", route_to_personas, ["persona_reaction"])
    # Join: every persona_reaction branch converges back here before the interrupt
    graph.add_edge("persona_reaction", "present_findings")
    # present_findings and human_approval_gate route themselves via Command(goto=...)
    graph.add_edge("challenge_and_rebuttal", "present_findings")
    graph.add_edge("synthesis", END)

    return graph


@contextmanager
def compiled_graph(db_path: str = DEFAULT_DB_PATH):
    """Context-managed compiled graph bound to a SQLite checkpointer.

    Must be used as a `with` block: SqliteSaver.from_conn_string holds the
    connection open for its lifetime, and resuming a run later requires
    reopening it against the same db_path/thread_id.
    """
    with SqliteSaver.from_conn_string(db_path) as checkpointer:
        graph = build_graph_definition()
        yield graph.compile(checkpointer=checkpointer)
