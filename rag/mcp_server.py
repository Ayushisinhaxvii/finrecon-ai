
"""FINRECON AI: read-only MCP tools for reconciliation investigations."""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any

import duckdb
from mcp.server.fastmcp import FastMCP

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "dev.duckdb"

logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("finrecon-mcp")

mcp = FastMCP("finrecon-ai")


def _query(sql: str, parameters: list[Any] | None = None) -> dict:
    """Execute one read-only query against the project database."""

    if not DB_PATH.exists():
        return {
            "status": "ERROR",
            "message": f"Database not found: {DB_PATH}",
        }

    connection = None

    try:
        connection = duckdb.connect(str(DB_PATH), read_only=True)
        cursor = connection.execute(sql, parameters or [])
        columns = [column[0] for column in cursor.description]
        rows = [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]

        return {
            "status": "SUCCESS",
            "row_count": len(rows),
            "results": rows,
        }

    except Exception as exc:
        logger.exception("Database query failed.")
        return {
            "status": "ERROR",
            "message": f"{type(exc).__name__}: {exc}",
        }

    finally:
        if connection is not None:
            connection.close()


def _json(data: dict) -> str:
    """Serialize tool results consistently."""
    return json.dumps(data, indent=2, default=str)


@mcp.tool()
async def get_incident_counts() -> str:
    """Count incidents grouped by incident type."""

    result = await asyncio.to_thread(
        _query,
        """
        SELECT incident_type, COUNT(*) AS incident_count
        FROM fct_reconciliation_incidents
        GROUP BY incident_type
        ORDER BY incident_type
        """,
    )
    return _json(result)


@mcp.tool()
async def list_incidents(
    incident_type: str = "",
    limit: int = 20,
) -> str:
    """List incidents, optionally filtering by exact incident type."""

    safe_limit = max(1, min(int(limit), 100))

    if incident_type.strip():
        sql = """
            SELECT *
            FROM fct_reconciliation_incidents
            WHERE incident_type = ?
            ORDER BY order_id
            LIMIT ?
        """
        parameters = [incident_type.strip().upper(), safe_limit]
    else:
        sql = """
            SELECT *
            FROM fct_reconciliation_incidents
            ORDER BY order_id
            LIMIT ?
        """
        parameters = [safe_limit]

    result = await asyncio.to_thread(_query, sql, parameters)
    return _json(result)


@mcp.tool()
async def get_reconciliation_status_counts() -> str:
    """Count reconciliation records grouped by status."""

    result = await asyncio.to_thread(
        _query,
        """
        SELECT reconciliation_status, COUNT(*) AS record_count
        FROM fct_reconciliation
        GROUP BY reconciliation_status
        ORDER BY reconciliation_status
        """,
    )
    return _json(result)


@mcp.tool()
async def get_incident_evidence(order_id: str) -> str:
    """Retrieve incident evidence for one exact order ID."""

    cleaned_order_id = order_id.strip()

    if not cleaned_order_id:
        return _json({
            "status": "ERROR",
            "message": "order_id cannot be empty.",
        })

    logger.info("Evidence request started for order_id=%s", cleaned_order_id)

    result = await asyncio.to_thread(
        _query,
        """
        SELECT *
        FROM fct_reconciliation_incidents
        WHERE order_id = ?
        ORDER BY incident_type
        """,
        [cleaned_order_id],
    )

    response = _json(result)
    logger.info("Evidence request completed for order_id=%s", cleaned_order_id)

    return response


if __name__ == "__main__":
    mcp.run(transport="stdio")
