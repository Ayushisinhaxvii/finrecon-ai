
"""FINRECON AI: read-only MCP server using Streamable HTTP."""

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

logger = logging.getLogger("finrecon-mcp-http")

mcp = FastMCP("finrecon-ai-http")

# Local-only server settings.
mcp.settings.host = "127.0.0.1"
mcp.settings.port = 8000


def query(sql: str, parameters: list[Any] | None = None) -> dict:
    """Execute a read-only query against the project database."""

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
        logger.exception("Database query failed")
        return {
            "status": "ERROR",
            "message": f"{type(exc).__name__}: {exc}",
        }

    finally:
        if connection is not None:
            connection.close()


def to_json(data: dict) -> str:
    return json.dumps(data, indent=2, default=str)


@mcp.tool()
def get_incident_counts() -> str:
    """Count incidents grouped by incident type."""

    return to_json(query("""
        SELECT incident_type, COUNT(*) AS incident_count
        FROM fct_reconciliation_incidents
        GROUP BY incident_type
        ORDER BY incident_type
    """))


@mcp.tool()
def list_incidents(
    incident_type: str = "",
    limit: int = 20,
) -> str:
    """List incidents, optionally filtering by exact incident type."""

    safe_limit = max(1, min(int(limit), 100))

    if incident_type.strip():
        result = query(
            """
            SELECT *
            FROM fct_reconciliation_incidents
            WHERE incident_type = ?
            ORDER BY order_id
            LIMIT ?
            """,
            [incident_type.strip().upper(), safe_limit],
        )
    else:
        result = query(
            """
            SELECT *
            FROM fct_reconciliation_incidents
            ORDER BY order_id
            LIMIT ?
            """,
            [safe_limit],
        )

    return to_json(result)


@mcp.tool()
def get_reconciliation_status_counts() -> str:
    """Count reconciliation records grouped by status."""

    return to_json(query("""
        SELECT reconciliation_status, COUNT(*) AS record_count
        FROM fct_reconciliation
        GROUP BY reconciliation_status
        ORDER BY reconciliation_status
    """))


@mcp.tool()
def get_incident_evidence(order_id: str) -> str:
    """Retrieve evidence for one exact order ID."""

    cleaned_order_id = order_id.strip()

    if not cleaned_order_id:
        return to_json({
            "status": "ERROR",
            "message": "order_id cannot be empty.",
        })

    logger.info("Fetching evidence for order_id=%s", cleaned_order_id)

    result = query(
        """
        SELECT *
        FROM fct_reconciliation_incidents
        WHERE order_id = ?
        ORDER BY incident_type
        """,
        [cleaned_order_id],
    )

    return to_json(result)


if __name__ == "__main__":
    logger.info("Starting FINRECON MCP on http://127.0.0.1:8000/mcp")
    mcp.run(transport="streamable-http")
