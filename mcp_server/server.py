"""Persona research / grounding MCP server.

Standalone SSE service (not stdio) — run as its own process so it's
demoable independently of the LangGraph app. Exposes:

- get_market_context(topic, persona_role) tool — calls through to the
  public duckduckgo-mcp-server (this server acts as an MCP CLIENT to it)
  instead of hitting a search API directly.
- persona_incentive_profile://{persona_id} resource — each persona's
  incentive structure and evaluation criteria, no longer hardcoded in
  the graph.
- log_challenge_outcome(persona_id, challenge, outcome) tool — persists
  to this server's own audit trail, separate from LangGraph state.

Run: python server.py  (serves http://127.0.0.1:8765/sse)

Built on mcp 2.x's MCPServer (the renamed successor to v1's FastMCP —
mcp.server.fastmcp is gone in 2.x; see the migration guide if this
looks unfamiliar).
"""

from __future__ import annotations

import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.server.mcpserver import MCPServer

from audit_log import append_entry
from personas import PERSONA_PROFILES

mcp = MCPServer("persona-research")

PERSONA_SEARCH_FRAMING = {
    "investor": "funding rounds comparable startups valuation market size",
    "customer": "reviews complaints user experience",
    "regulator": "regulation compliance requirements legal framework",
}


def _duckduckgo_command() -> str:
    """Locate the duckduckgo-mcp-server console script installed in this
    venv (its Scripts/bin dir sits next to the running python.exe), so we
    don't depend on it being separately added to PATH.
    """
    scripts_dir = Path(sys.executable).parent
    for name in ("duckduckgo-mcp-server.exe", "duckduckgo-mcp-server"):
        candidate = scripts_dir / name
        if candidate.exists():
            return str(candidate)
    return "duckduckgo-mcp-server"


@mcp.resource("persona_incentive_profile://{persona_id}")
def persona_incentive_profile(persona_id: str) -> dict:
    """Exposes a persona's incentive structure and evaluation criteria."""
    profile = PERSONA_PROFILES.get(persona_id)
    if profile is None:
        raise ValueError(f"Unknown persona_id: {persona_id}")
    return profile


@mcp.tool()
async def get_market_context(topic: str, persona_role: str) -> str:
    """Pull real-world signal relevant to a persona reacting to `topic`
    (funding comparables for investor, reviews/complaints for customer,
    regulatory framework snippets for regulator).

    Acts as an MCP client to the public duckduckgo-mcp-server rather
    than calling a search API directly.
    """
    framing = PERSONA_SEARCH_FRAMING.get(persona_role, "")
    query = f"{topic} {framing}".strip()

    server_params = StdioServerParameters(command=_duckduckgo_command(), args=[])
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "search", {"query": query, "max_results": 5}
            )
            text_parts = [
                block.text for block in result.content if hasattr(block, "text")
            ]
            return "\n".join(text_parts) if text_parts else "No market context found."


@mcp.tool()
def log_challenge_outcome(persona_id: str, challenge: str, outcome: str) -> str:
    """Persist a challenge/rebuttal outcome to this server's own audit
    trail — separate from LangGraph's checkpointed `challenge_log`.
    """
    entry = append_entry(persona_id, challenge, outcome)
    return f"Logged at {entry['timestamp']}"


if __name__ == "__main__":
    mcp.run(transport="sse", host="127.0.0.1", port=8765, sse_path="/sse")
