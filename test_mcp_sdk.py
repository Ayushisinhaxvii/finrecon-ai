
import asyncio
import sys
import time
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

PROJECT_ROOT = Path(__file__).resolve().parent


async def main():
    server = StdioServerParameters(
        command=sys.executable,
        args=["-u", "-m", "rag.mcp_server"],
        cwd=str(PROJECT_ROOT),
    )

    print("Starting MCP server...", flush=True)

    async with stdio_client(server, errlog=sys.stderr) as (read, write):
        async with ClientSession(read, write) as session:
            await asyncio.wait_for(session.initialize(), timeout=15)
            print("MCP initialized.", flush=True)

            print("Calling evidence tool with a 45-second timeout...", flush=True)
            start = time.perf_counter()

            result = await asyncio.wait_for(
                session.call_tool(
                    "get_incident_evidence",
                    arguments={"order_id": "ORD000054"},
                ),
                timeout=45,
            )

            elapsed = time.perf_counter() - start
            print(f"Tool completed in {elapsed:.2f} seconds.", flush=True)
            print("Tool error flag:", result.isError, flush=True)

            for item in result.content:
                if hasattr(item, "text"):
                    print(item.text, flush=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print(
            f"FAILED: {type(exc).__name__}: {exc}",
            file=sys.stderr,
            flush=True,
        )
        raise
