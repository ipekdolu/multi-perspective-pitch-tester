"""MCP client helpers for the graph nodes.

The LangGraph app is an MCP CLIENT to the standalone persona-research
server (mcp_server/, run separately over SSE). Node functions in this
app are synchronous (see nodes.py), so each helper here opens a short-
lived session per call via asyncio.run() rather than requiring the
whole graph/CLI to become async — the simplest change that gets nodes
talking to the server without restructuring how the graph is invoked.
"""

from __future__ import annotations

import asyncio
import json
import os

from mcp import ClientSession
from mcp.client.sse import sse_client

MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://127.0.0.1:8765/sse")


async def _read_persona_profile_async(persona_id: str) -> dict:
    async with sse_client(MCP_SERVER_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            resource = await session.read_resource(
                f"persona_incentive_profile://{persona_id}"
            )
            return json.loads(resource.contents[0].text)


async def _get_market_context_async(topic: str, persona_role: str) -> str:
    async with sse_client(MCP_SERVER_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "get_market_context", {"topic": topic, "persona_role": persona_role}
            )
            parts = [b.text for b in result.content if hasattr(b, "text")]
            return "\n".join(parts)


async def _log_challenge_outcome_async(
    persona_id: str, challenge: str, outcome: str
) -> None:
    async with sse_client(MCP_SERVER_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            await session.call_tool(
                "log_challenge_outcome",
                {"persona_id": persona_id, "challenge": challenge, "outcome": outcome},
            )


def fetch_persona_profile(persona_id: str) -> dict:
    return asyncio.run(_read_persona_profile_async(persona_id))


def fetch_market_context(topic: str, persona_role: str) -> str:
    return asyncio.run(_get_market_context_async(topic, persona_role))


def log_challenge_outcome(persona_id: str, challenge: str, outcome: str) -> None:
    asyncio.run(_log_challenge_outcome_async(persona_id, challenge, outcome))
