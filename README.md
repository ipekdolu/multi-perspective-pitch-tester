# Multi-perspective pitch tester

Pitch an idea; get pushback from an investor, a customer, and a regulator — each arguing from their own incentive, not from "be helpful." Challenge any of them, watch them hold their ground or genuinely concede, then get a synthesis of where they agree, where they diverge, and the biggest risk raised.

**Live app:** https://multi-perspective-pitch-tester.vercel.app
(backend: Render free tier — the first request after a period of inactivity can take 30-60s to wake up)

## Why this exists

Most "AI pitch feedback" tools return one blended, agreeable summary. That's not how real diligence works — an investor, a customer, and a regulator are structurally incapable of agreeing, because they're optimizing for different things. This project tests whether an agentic system can hold three genuinely distinct, adversarial perspectives simultaneously, let a human interrogate each one, and then synthesize the *disagreement* itself as the useful output — rather than papering over it.

It's built as a demonstration of agentic system design for AI transformation / consulting / AI & data roles: multi-agent orchestration with human-in-the-loop control, tool use via a real protocol (not a hardcoded function call), and a measurable evaluation approach — not just a chatbot wrapper.

## Architecture

```
┌─────────────────┐      HTTP       ┌──────────────────────┐      MCP (SSE)     ┌──────────────────────┐
│  React frontend  │ ───────────────▶│   FastAPI backend     │ ──────────────────▶│  persona-research MCP │
│  (Vercel)         │◀─────────────── │   (Render)             │◀────────────────── │  server (Render)       │
└─────────────────┘                  │                        │                    │                        │
                                      │  LangGraph state       │                    │ - persona incentive    │
                                      │  machine (SQLite       │                    │   profiles (resource)  │
                                      │  checkpointed)         │                    │ - live market context  │
                                      └──────────┬─────────────┘                    │   (MCP client to       │
                                                 │                                  │   duckduckgo-mcp-server)│
                                                 │                                  │ - challenge/outcome     │
                                                 ▼                                  │   audit log (JSONL)     │
                                      ┌──────────────────────┐                     └──────────────────────┘
                                      │  Claude (Anthropic)    │
                                      │  via langchain-anthropic│
                                      └──────────────────────┘

                                      ┌──────────────────────┐
                                      │  Langfuse               │  <- tracing + sampled online scoring
                                      │  (live runs) +          │     + offline golden-dataset experiment
                                      │  offline eval harness   │
                                      └──────────────────────┘
```

### The graph (LangGraph)

Seven nodes, one `StateGraph`:

1. **intake** — takes the raw pitch text. (Deliberately a stub — see [Known limitations](#known-limitations).)
2. **route_to_personas** — fans out via LangGraph's `Send` API into three parallel branches, one per persona. No incentive data lives here; each branch fetches its own.
3. **persona_reaction** *(×3, parallel)* — each branch acts as an MCP client twice: reads its persona's incentive profile from the `persona_incentive_profile://{id}` resource, and calls `get_market_context` to ground its reaction in live search results instead of the model's own guesswork. Then calls Claude with a system prompt built from real incentive/evaluation-criteria data, not a hardcoded persona description.
4. **present_findings** — join point; `interrupt()`s to hand control to a human, who can either challenge a specific persona or move on.
5. **challenge_and_rebuttal** — replays the persona's full thread as message history and asks the model to genuinely decide *hold* vs. *concede* via structured output (`RebuttalDecision`), then logs the outcome back to the MCP server's own audit trail.
6. **human_approval_gate** — second `interrupt()`; a human approves (moves to synthesis) or rejects (loops back for another challenge round).
7. **synthesis** — reads the full transcript (not just the challenge log) and produces structured `agreement` / `divergence` / `biggest_risk` output.

Interrupt/resume is backed by `SqliteSaver`, so a run's state survives across separate process invocations — the CLI (`app/main.py`) deliberately runs each step as its own process to prove this isn't just in-memory continuation.

### Why MCP, not a hardcoded function call

Persona incentive data and market-grounding search live behind a **separate, standalone MCP server** (`mcp_server/`), not inside the graph's own code. The backend is an MCP *client* to it; the MCP server is itself an MCP *client* to the public `duckduckgo-mcp-server` for search. This is the actual point of the protocol: the persona-research service is independently runnable, testable (`mcp_server/manual_check.py`), and swappable without touching graph logic — e.g. incentive profiles could move to a database or a different search provider without the graph noticing.

### Why structured output everywhere it matters

Every decision that gets used programmatically downstream (challenge hold/concede, synthesis output, eval judge scores) is forced through Pydantic structured output rather than parsed from free text. This is what makes the challenge outcome reliable enough to double as the eval golden-trace format, and what makes judge scores aggregable rather than another parsing problem.

## Evaluation

Two LLM-as-judge scorers (`backend/app/eval/judges.py`), deliberately run on a cheaper model (`claude-sonnet-5`) than the personas themselves (grading generated transcripts is a cheaper-model task):

- **Judge 1 — persona consistency**: reads one persona's thread in isolation, scores whether it stayed in character (argued from its stated incentive, didn't drift into generic-assistant helpfulness) and, where a challenge occurred, whether the hold/concede decision was actually earned rather than reflexive.
- **Judge 2 — synthesis quality**: compares the actual synthesis against a hand-written golden reference, scored on substance (not wording) for agreement/divergence/risk match.

**Offline**: an 8-case hand-built golden dataset (`eval/golden_dataset.py`) spanning 4 archetypes — mostly-agree, sharp-divergence, should-concede-strong-challenge, should-hold-weak-challenge — run through both judges via `eval/run_eval.py`, with a Langfuse dataset-experiment variant (`eval/run_langfuse_experiment.py`) for tracked runs.

**Online**: Judge 1 only (Judge 2 needs a golden reference that live user pitches don't have) runs on a sampled fraction (`LANGFUSE_ONLINE_SAMPLE_RATE`, default 20%) of real deployed runs, scores attached to the run's Langfuse trace. Langfuse is pure observability — the app runs identically with zero Langfuse keys set.

## Known limitations

- **`intake` is a stub.** It wraps the raw pitch string directly into the structured `pitch` field rather than running an LLM extraction pass to pull out claims/target-market/ask separately. This was an explicit scope decision, not an oversight — the project's focus is the multi-perspective adversarial loop, not pitch parsing.
- **Market grounding degrades gracefully, not silently.** The MCP server's `get_market_context` tool spawns `duckduckgo-mcp-server` as a subprocess; on Render's free-tier container this subprocess reliably fails (likely missing browser binaries), so personas run without live search grounding in the deployed version — they still work, but the "give me real comps" signal is absent there. Works locally.
- **Render free tier**: both backend and MCP server spin down after ~15 minutes idle; the checkpoint SQLite file is on ephemeral disk, so an in-progress run could theoretically lose state across a spin-down/restart cycle. Not yet hit in practice, but the known fix (swap `SqliteSaver` for Render's free Postgres) isn't implemented since it hasn't been confirmed necessary.

## Running locally

Three processes, in this order:

```bash
# 1. MCP server (persona-research)
cd mcp_server
python -m venv .venv && .venv/Scripts/activate  # or source .venv/bin/activate
pip install -r requirements.txt
python server.py   # serves http://127.0.0.1:8765/sse

# 2. Backend (LangGraph + FastAPI)
cd backend
python -m venv .venv && .venv/Scripts/activate
pip install -e .
cp .env.example .env   # fill in ANTHROPIC_API_KEY at minimum
python -m app.api      # serves http://127.0.0.1:8000

# 3. Frontend (React + Vite)
cd frontend
npm install
cp .env.example .env.local   # points at http://127.0.0.1:8000 by default
npm run dev             # serves http://127.0.0.1:5173
```

There's also a CLI (`python -m app.main start/challenge/done/approve/reject/show --thread <id>`) if you'd rather drive a run without the frontend.

### Running the eval suite

```bash
cd backend
python -m app.eval.run_eval   # 8-case golden dataset, both judges, printed summary
```

Uses real Anthropic API calls (persona generation + judge scoring) — budget accordingly, or override `PITCH_TESTER_MODEL`/`EVAL_JUDGE_MODEL` to cheaper models first.

## Repo structure

```
backend/          LangGraph app, FastAPI wrapper, CLI, eval suite
  app/graph/       state schema, node functions, graph wiring
  app/eval/        golden dataset, LLM judges, offline/Langfuse runners
mcp_server/        standalone MCP server: persona profiles, market context, audit log
frontend/          React + Vite + TS UI
render.yaml        Render Blueprint (backend + MCP server, both free tier)
```

## Tech stack

LangGraph (state machine, `Send` fan-out, `interrupt`/`Command` resume, SQLite checkpointing) · MCP (`mcp` 2.x SDK, SSE transport) · Claude via `langchain-anthropic` · FastAPI · React/Vite/TypeScript · Langfuse (tracing + LLM-as-judge scoring) · Render + Vercel
