
import asyncio

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def main():
    url = "http://127.0.0.1:8000/mcp"

    print("Connecting to FINRECON MCP over HTTP...", flush=True)

    async with streamable_http_client(url) as streams:
        read_stream = streams[0]
        write_stream = streams[1]

        async with ClientSession(read_stream, write_stream) as session:
            await asyncio.wait_for(session.initialize(), timeout=15)
            print("MCP initialized successfully.", flush=True)

            tools = await asyncio.wait_for(session.list_tools(), timeout=15)
            print(
                "Discovered tools:",
                [tool.name for tool in tools.tools],
                flush=True,
            )

            print("Calling evidence tool...", flush=True)

            result = await asyncio.wait_for(
                session.call_tool(
                    "get_incident_evidence",
                    arguments={"order_id": "ORD000054"},
                ),
                timeout=30,
            )

            print("Tool error:", result.isError, flush=True)

            for item in result.content:
                if hasattr(item, "text"):
                    print(item.text, flush=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print(f"HTTP MCP test failed: {type(exc).__name__}: {exc}")
        raise
