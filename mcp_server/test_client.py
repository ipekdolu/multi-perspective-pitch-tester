"""Bare MCP client script to test server.py independently, before wiring
it into the LangGraph app. Run server.py in one process (SSE on
127.0.0.1:8765), then run this script separately.
"""

import asyncio

from mcp import ClientSession
from mcp.client.sse import sse_client


async def main():
    async with sse_client("http://127.0.0.1:8765/sse") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            print("=== list_tools ===")
            tools = await session.list_tools()
            for t in tools.tools:
                print(f"- {t.name}: {t.description}")

            print("\n=== read resource: persona_incentive_profile://investor ===")
            resource = await session.read_resource(
                "persona_incentive_profile://investor"
            )
            for content in resource.contents:
                print(content.text)

            print("\n=== call_tool: log_challenge_outcome ===")
            result = await session.call_tool(
                "log_challenge_outcome",
                {
                    "persona_id": "investor",
                    "challenge": "test challenge from bare client",
                    "outcome": "held",
                },
            )
            for block in result.content:
                if hasattr(block, "text"):
                    print(block.text)

            print("\n=== call_tool: get_market_context (investor) ===")
            result = await session.call_tool(
                "get_market_context",
                {"topic": "Anthropic Claude API", "persona_role": "investor"},
            )
            for block in result.content:
                if hasattr(block, "text"):
                    print(block.text[:1500])


if __name__ == "__main__":
    asyncio.run(main())
