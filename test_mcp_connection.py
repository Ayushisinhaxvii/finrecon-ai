
import asyncio
import sys
import time

from langchain_mcp_adapters.client import MultiServerMCPClient


async def main():
    client = MultiServerMCPClient(
        {
            "finrecon": {
                "transport": "stdio",
                "command": sys.executable,
                "args": ["-u", "-m", "rag.mcp_server"],
            }
        }
    )

    start = time.perf_counter()

    print("Connecting and discovering tools...", flush=True)

    tools = await asyncio.wait_for(
        client.get_tools(),
        timeout=20,
    )

    print(
        f"Tools discovered in {time.perf_counter() - start:.2f}s",
        flush=True,
    )
    print("Tools:", [tool.name for tool in tools], flush=True)

    tool = next(
        (
            item for item in tools
            if item.name == "get_incident_evidence"
        ),
        None,
    )

    if tool is None:
        raise RuntimeError("Evidence tool was not discovered.")

    print("Calling evidence tool (15-second limit)...", flush=True)

    try:
        result = await asyncio.wait_for(
            tool.ainvoke({"order_id": "ORD000054"}),
            timeout=15,
        )

        print(
            f"Tool completed in {time.perf_counter() - start:.2f}s",
            flush=True,
        )
        print("Result:", result, flush=True)

    except asyncio.TimeoutError:
        print(
            "TIMEOUT: Tool call did not return within 15 seconds.",
            flush=True,
        )


if __name__ == "__main__":
    asyncio.run(main())
