"""CLI to drive the pitch-tester graph one step at a time.

Each subcommand is meant to be run as its OWN `python` process invocation,
not chained in-process. That's the point: closing the process and
re-opening the SQLite checkpointer in a fresh run is what actually proves
resume-from-checkpoint works, rather than just resuming within one
long-lived script that never lost its state anyway.

Usage:
    python -m app.main start   --thread t1 --pitch "..."
    python -m app.main challenge --thread t1 --persona investor --text "..."
    python -m app.main done    --thread t1
    python -m app.main approve --thread t1
    python -m app.main reject  --thread t1
    python -m app.main show    --thread t1
"""

from __future__ import annotations

import argparse
import json

from dotenv import load_dotenv
from langgraph.types import Command

load_dotenv()

from app.graph.build import compiled_graph

DB_PATH = "pitch_tester_checkpoints.sqlite"


def _print_state_summary(state) -> None:
    values = state.values
    print(f"-- next node(s): {state.next}")
    print(f"-- round_count: {values.get('round_count')}")
    print(f"-- human_approval: {values.get('human_approval')}")
    print("-- persona_threads:")
    for persona_id, msgs in values.get("persona_threads", {}).items():
        for m in msgs:
            print(f"     [{persona_id}] {m['role']}: {m['content']}")
    print("-- challenge_log:")
    for c in values.get("challenge_log", []):
        print(f"     {c['persona_id']}: {c['outcome']} -- {c['challenge_text']}")
    if values.get("synthesis"):
        print("-- synthesis:")
        print(json.dumps(values["synthesis"], indent=2))
    if state.tasks:
        for task in state.tasks:
            for interrupt in task.interrupts:
                print(f"-- INTERRUPTED with payload: {interrupt.value}")


def cmd_start(args: argparse.Namespace) -> None:
    config = {"configurable": {"thread_id": args.thread}}
    with compiled_graph(DB_PATH) as graph:
        result = graph.invoke({"raw_pitch": args.pitch}, config=config)
        state = graph.get_state(config)
        _print_state_summary(state)


def cmd_challenge(args: argparse.Namespace) -> None:
    config = {"configurable": {"thread_id": args.thread}}
    with compiled_graph(DB_PATH) as graph:
        graph.invoke(
            Command(
                resume={
                    "action": "challenge",
                    "persona_id": args.persona,
                    "text": args.text,
                }
            ),
            config=config,
        )
        state = graph.get_state(config)
        _print_state_summary(state)


def cmd_done(args: argparse.Namespace) -> None:
    config = {"configurable": {"thread_id": args.thread}}
    with compiled_graph(DB_PATH) as graph:
        graph.invoke(Command(resume={"action": "done"}), config=config)
        state = graph.get_state(config)
        _print_state_summary(state)


def cmd_decide(decision: str, args: argparse.Namespace) -> None:
    config = {"configurable": {"thread_id": args.thread}}
    with compiled_graph(DB_PATH) as graph:
        graph.invoke(Command(resume={"decision": decision}), config=config)
        state = graph.get_state(config)
        _print_state_summary(state)


def cmd_show(args: argparse.Namespace) -> None:
    config = {"configurable": {"thread_id": args.thread}}
    with compiled_graph(DB_PATH) as graph:
        state = graph.get_state(config)
        _print_state_summary(state)


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    p_start = sub.add_parser("start")
    p_start.add_argument("--thread", required=True)
    p_start.add_argument("--pitch", required=True)
    p_start.set_defaults(func=cmd_start)

    p_challenge = sub.add_parser("challenge")
    p_challenge.add_argument("--thread", required=True)
    p_challenge.add_argument("--persona", required=True)
    p_challenge.add_argument("--text", required=True)
    p_challenge.set_defaults(func=cmd_challenge)

    p_done = sub.add_parser("done")
    p_done.add_argument("--thread", required=True)
    p_done.set_defaults(func=cmd_done)

    p_approve = sub.add_parser("approve")
    p_approve.add_argument("--thread", required=True)
    p_approve.set_defaults(func=lambda a: cmd_decide("approved", a))

    p_reject = sub.add_parser("reject")
    p_reject.add_argument("--thread", required=True)
    p_reject.set_defaults(func=lambda a: cmd_decide("rejected", a))

    p_show = sub.add_parser("show")
    p_show.add_argument("--thread", required=True)
    p_show.set_defaults(func=cmd_show)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
