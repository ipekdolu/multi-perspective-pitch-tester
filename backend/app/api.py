"""FastAPI wrapper around the LangGraph app.

Thin layer: each endpoint is the HTTP equivalent of one of main.py's CLI
subcommands, reusing the same compiled_graph() (SQLite-checkpointed) so
behavior matches what Phases 1-4 already proved works. This exists
because Phase 5 needs the human approval gate operable from a UI rather
than the CLI — this is the backend that minimal UI talks to.

Run: python -m app.api  (serves http://127.0.0.1:8000, UI at /)
"""

from __future__ import annotations

import uuid
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from langgraph.types import Command
from pydantic import BaseModel

from app.graph.build import compiled_graph
from app.langfuse_online import get_callbacks, make_trace_id, maybe_score_run

DB_PATH = "pitch_tester_checkpoints.sqlite"
STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="pitch-tester")


class StartRequest(BaseModel):
    pitch: str


class ChallengeRequest(BaseModel):
    persona_id: str
    text: str


def _config(thread_id: str) -> tuple[dict, str | None]:
    """Graph invoke config, with Langfuse callbacks attached to a trace
    seeded from thread_id -- a no-op callbacks list if Langfuse isn't
    configured (see langfuse_online.py). Returns (config, trace_id);
    trace_id is returned separately (not embedded in config) since
    LangGraph's RunnableConfig isn't a free-form dict for extra keys.
    """
    trace_id = make_trace_id(thread_id)
    config = {
        "configurable": {"thread_id": thread_id},
        "callbacks": get_callbacks(trace_id),
    }
    return config, trace_id


def _serialize_state(thread_id: str, state) -> dict:
    values = state.values
    interrupt_payload = None
    for task in state.tasks:
        for i in task.interrupts:
            interrupt_payload = i.value

    return {
        "thread_id": thread_id,
        "next_nodes": list(state.next),
        "round_count": values.get("round_count"),
        "human_approval": values.get("human_approval"),
        "persona_threads": values.get("persona_threads", {}),
        "challenge_log": values.get("challenge_log", []),
        "synthesis": values.get("synthesis"),
        "interrupt": interrupt_payload,
    }


@app.post("/runs")
def start_run(req: StartRequest) -> dict:
    thread_id = uuid.uuid4().hex[:12]
    config, trace_id = _config(thread_id)
    with compiled_graph(DB_PATH) as graph:
        graph.invoke({"raw_pitch": req.pitch}, config=config)
        state = graph.get_state(config)
    maybe_score_run(trace_id, state.values)
    return _serialize_state(thread_id, state)


@app.get("/runs/{thread_id}")
def get_run(thread_id: str) -> dict:
    config, _ = _config(thread_id)
    with compiled_graph(DB_PATH) as graph:
        state = graph.get_state(config)
    if not state.values:
        raise HTTPException(status_code=404, detail="unknown thread_id")
    return _serialize_state(thread_id, state)


@app.post("/runs/{thread_id}/challenge")
def challenge_run(thread_id: str, req: ChallengeRequest) -> dict:
    config, trace_id = _config(thread_id)
    with compiled_graph(DB_PATH) as graph:
        graph.invoke(
            Command(
                resume={
                    "action": "challenge",
                    "persona_id": req.persona_id,
                    "text": req.text,
                }
            ),
            config=config,
        )
        state = graph.get_state(config)
    maybe_score_run(trace_id, state.values)
    return _serialize_state(thread_id, state)


@app.post("/runs/{thread_id}/done")
def done_run(thread_id: str) -> dict:
    config, trace_id = _config(thread_id)
    with compiled_graph(DB_PATH) as graph:
        graph.invoke(Command(resume={"action": "done"}), config=config)
        state = graph.get_state(config)
    maybe_score_run(trace_id, state.values)
    return _serialize_state(thread_id, state)


@app.post("/runs/{thread_id}/approve")
def approve_run(thread_id: str) -> dict:
    config, trace_id = _config(thread_id)
    with compiled_graph(DB_PATH) as graph:
        graph.invoke(Command(resume={"decision": "approved"}), config=config)
        state = graph.get_state(config)
    maybe_score_run(trace_id, state.values)
    return _serialize_state(thread_id, state)


@app.post("/runs/{thread_id}/reject")
def reject_run(thread_id: str) -> dict:
    config, trace_id = _config(thread_id)
    with compiled_graph(DB_PATH) as graph:
        graph.invoke(Command(resume={"decision": "rejected"}), config=config)
        state = graph.get_state(config)
    maybe_score_run(trace_id, state.values)
    return _serialize_state(thread_id, state)


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.api:app", host="127.0.0.1", port=8000, reload=False)
