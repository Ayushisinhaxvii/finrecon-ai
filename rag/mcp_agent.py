
"""FINRECON AI: MCP-backed incident investigation and proposal generation."""

import asyncio
import json
import logging
import os
import re
from typing import Any

from dotenv import load_dotenv
from google import genai
from langchain_mcp_adapters.client import MultiServerMCPClient

load_dotenv()

logger = logging.getLogger(__name__)

MCP_URL = "http://127.0.0.1:8000/mcp"
GEMINI_MODEL = "gemini-3.8-flash"

MCP_SERVER_CONFIG = {
    "finrecon": {
        "transport": "streamable_http",
        "url": MCP_URL,
    }
}


def _find_order_id(question: str) -> str | None:
    """Extract an order ID from a question."""
    match = re.search(r"\bORD[A-Z0-9_-]+\b", question, re.IGNORECASE)
    return match.group(0).upper() if match else None


def _is_count_question(question: str) -> bool:
    """Identify incident-count questions."""
    text = question.lower()
    return any(
        phrase in text
        for phrase in (
            "how many",
            "count",
            "number of incidents",
            "incident counts",
            "total incidents",
            "breakdown",
        )
    )


async def _call_mcp_tool(
    tool_name: str,
    arguments: dict[str, Any] | None = None,
) -> tuple[Any, list[str]]:
    """Discover and invoke an MCP tool over Streamable HTTP."""
    client = MultiServerMCPClient(MCP_SERVER_CONFIG)
    tools = await asyncio.wait_for(client.get_tools(), timeout=20)

    tool_names = [tool.name for tool in tools]
    selected_tool = next(
        (tool for tool in tools if tool.name == tool_name),
        None,
    )

    if selected_tool is None:
        raise RuntimeError(
            f"MCP tool '{tool_name}' was not found. "
            f"Available tools: {tool_names}"
        )

    result = await asyncio.wait_for(
        selected_tool.ainvoke(arguments or {}),
        timeout=45,
    )

    return result, tool_names


async def _retrieve_evidence(
    question: str,
) -> tuple[Any, list[str], str]:
    """Route the question to the appropriate read-only MCP tool."""
    order_id = _find_order_id(question)

    if order_id:
        result, names = await _call_mcp_tool(
            "get_incident_evidence",
            {"order_id": order_id},
        )
        return result, names, "MCP_HTTP_EVIDENCE"

    if _is_count_question(question):
        result, names = await _call_mcp_tool(
            "get_incident_counts",
            {},
        )
        return result, names, "MCP_HTTP_INCIDENT_COUNTS"

    result, names = await _call_mcp_tool(
        "list_incidents",
        {"limit": 20},
    )
    return result, names, "MCP_HTTP_INCIDENT_LIST"


def _result_text(result: Any) -> str:
    """Extract text from MCP tool output."""
    if isinstance(result, str):
        return result

    if isinstance(result, dict):
        if isinstance(result.get("text"), str):
            return result["text"]

        if isinstance(result.get("content"), list):
            return _result_text(result["content"])

        return json.dumps(result, default=str)

    if isinstance(result, list):
        parts = []

        for item in result:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and isinstance(
                item.get("text"), str
            ):
                parts.append(item["text"])
            elif hasattr(item, "text") and isinstance(item.text, str):
                parts.append(item.text)

        if parts:
            return "\n".join(parts)

    content = getattr(result, "content", None)
    if isinstance(content, list):
        return _result_text(content)

    raise TypeError(
        f"Unsupported MCP result type: {type(result).__name__}"
    )


def _parse_tool_result(result: Any) -> dict:
    """Parse and validate MCP JSON."""
    try:
        parsed = json.loads(_result_text(result))
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        return {
            "status": "ERROR",
            "message": f"Could not parse MCP JSON: {exc}",
        }

    if not isinstance(parsed, dict):
        return {
            "status": "ERROR",
            "message": "MCP returned an unexpected JSON structure.",
        }

    return parsed


def _gemini_background_request(prompt: str) -> str:
    """Create a background Gemini interaction and poll until completion."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY is missing. Check the root .env file."
        )

    client = genai.Client(api_key=api_key)

    try:
        # Background mode avoids holding one long HTTP request open.
        interaction = client.interactions.create(
            model=GEMINI_MODEL,
            input=prompt,
            background=True,
        )

        interaction_id = getattr(interaction, "id", None)
        if not interaction_id:
            raise RuntimeError(
                "Gemini did not return an interaction ID."
            )

        # Allow up to 5 minutes for server-side completion.
        import time

        deadline = time.monotonic() + 300

        while time.monotonic() < deadline:
            status = getattr(interaction, "status", None)

            if status == "completed":
                answer = getattr(interaction, "output_text", None)
                if isinstance(answer, str) and answer.strip():
                    return answer.strip()

                raise RuntimeError(
                    "Gemini completed but returned no text output."
                )

            if status in ("failed", "cancelled", "requires_action"):
                raise RuntimeError(
                    f"Gemini interaction ended with status: {status}"
                )

            time.sleep(3)
            interaction = client.interactions.get(id=interaction_id)

        raise TimeoutError(
            "Gemini background interaction did not finish within 5 minutes."
        )

    finally:
        client.close()


async def _ask_gemini(
    question: str,
    evidence: dict,
    *,
    proposal_mode: bool = False,
) -> str:
    """Generate an evidence-grounded answer using Gemini."""
    if evidence.get("status") != "SUCCESS":
        raise RuntimeError(
            "Cannot analyze evidence because MCP did not return SUCCESS."
        )

    if proposal_mode:
        task = """
Prepare a proposed incident-resolution action for human review.

Use these headings:
FINDINGS
PROPOSED ACTION
REASON
REVIEW STATUS

Use only the supplied evidence. Do not invent facts. Do not claim a
correction was executed. Human approval is required. Do not recommend
changing financial amounts without verified supporting evidence.
Keep the response concise.
"""
    else:
        task = """
Explain the incident concisely:
1. What the evidence shows.
2. Relevant payment, refund, and settlement amounts.
3. What remains uncertain.
4. The next verification step.

Use only the supplied evidence. Do not invent facts, present a suspected
cause as confirmed, or claim that a correction has been applied.
"""

    prompt = f"""
You are the FINRECON AI reconciliation investigator.

USER QUESTION:
{question}

MCP EVIDENCE:
{json.dumps(evidence, indent=2, default=str)}

TASK:
{task}
"""

    try:
        # The SDK request and polling are blocking, so run them in a worker
        # thread rather than blocking the application's async event loop.
        return await asyncio.to_thread(
            _gemini_background_request,
            prompt,
        )
    except Exception as exc:
        logger.exception("Gemini request failed")
        raise RuntimeError(
            f"Gemini request failed ({type(exc).__name__}): {exc}"
        ) from exc


async def investigate(question: str) -> dict:
    """Retrieve evidence and explain an incident."""
    cleaned_question = question.strip()

    if not cleaned_question:
        return {
            "status": "ERROR",
            "route": "MCP_HTTP",
            "question": question,
            "answer": "Please enter an investigation question.",
            "tool_evidence": None,
            "tools_available": [],
        }

    route = "MCP_HTTP"
    tool_names: list[str] = []
    evidence = None

    try:
        raw_result, tool_names, route = await _retrieve_evidence(
            cleaned_question
        )
        evidence = _parse_tool_result(raw_result)

        if evidence.get("status") != "SUCCESS":
            return {
                "status": "ERROR",
                "route": route,
                "question": cleaned_question,
                "answer": (
                    "MCP evidence retrieval failed: "
                    + str(evidence.get("message", evidence.get("status")))
                ),
                "tool_evidence": evidence,
                "tools_available": tool_names,
            }

        answer = await _ask_gemini(cleaned_question, evidence)

        return {
            "status": "SUCCESS",
            "route": route,
            "question": cleaned_question,
            "answer": answer,
            "tool_evidence": evidence,
            "tools_available": tool_names,
        }

    except Exception as exc:
        logger.exception("Incident investigation failed")
        return {
            "status": "ERROR",
            "route": route,
            "question": cleaned_question,
            "answer": f"Investigation failed: {type(exc).__name__}: {exc}",
            "tool_evidence": evidence,
            "tools_available": tool_names,
        }


async def generate_incident_proposal(
    question: str,
    incident_id: str | None = None,
) -> dict:
    """Prepare a reviewable proposal without executing financial changes."""
    cleaned_question = question.strip()

    route = "MCP_HTTP"
    tool_names: list[str] = []
    evidence = None

    try:
        raw_result, tool_names, route = await _retrieve_evidence(
            cleaned_question
        )
        evidence = _parse_tool_result(raw_result)

        if evidence.get("status") != "SUCCESS":
            return {
                "status": "ERROR",
                "incident_id": incident_id,
                "answer": (
                    "Cannot generate a proposal without valid MCP evidence."
                ),
                "proposed_action": None,
                "tool_evidence": evidence,
                "tools_available": tool_names,
                "route": route,
                "execution_status": "NOT_EXECUTED",
            }

        answer = await _ask_gemini(
            cleaned_question,
            evidence,
            proposal_mode=True,
        )

        match = re.search(
            r"PROPOSED ACTION\s*:?\s*(.*?)(?=\nREASON\b|\nREVIEW STATUS\b|\Z)",
            answer,
            re.IGNORECASE | re.DOTALL,
        )

        return {
            "status": "NEEDS_REVIEW",
            "incident_id": incident_id,
            "answer": answer,
            "proposed_action": match.group(1).strip() if match else None,
            "tool_evidence": evidence,
            "tools_available": tool_names,
            "route": route,
            "execution_status": "NOT_EXECUTED",
        }

    except Exception as exc:
        logger.exception("Incident proposal generation failed")
        return {
            "status": "ERROR",
            "incident_id": incident_id,
            "answer": (
                f"Proposal generation failed: {type(exc).__name__}: {exc}"
            ),
            "proposed_action": None,
            "tool_evidence": evidence,
            "tools_available": tool_names,
            "route": route,
            "execution_status": "NOT_EXECUTED",
        }


def investigate_sync(question: str) -> dict:
    """Synchronous entry point for Streamlit and scripts."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(investigate(question))

    raise RuntimeError(
        "An event loop is already running; use await investigate(question)."
    )


def generate_incident_proposal_sync(
    question: str,
    incident_id: str | None = None,
) -> dict:
    """Synchronous proposal entry point for Streamlit and scripts."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(
            generate_incident_proposal(question, incident_id)
        )

    raise RuntimeError(
        "An event loop is already running; "
        "use await generate_incident_proposal(...)."
    )
