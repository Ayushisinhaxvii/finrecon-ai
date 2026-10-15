
from rag.mcp_agent import investigate_sync


if __name__ == "__main__":
    result = investigate_sync(
        "Investigate the settlement mismatch for ORD000054"
    )

    print("Status:", result.get("status"))
    print("Route:", result.get("route"))
    print("Tools discovered:", result.get("tools_available"))
    print("\nAnswer:\n", result.get("answer"))
    print("\nEvidence:\n", result.get("tool_evidence"))
