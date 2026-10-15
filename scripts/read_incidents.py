
from pathlib import Path
import duckdb

# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Existing DuckDB database created by dbt
DB_PATH = (
    PROJECT_ROOT
    / "dbt"
    / "finrecon"
    / "dev.duckdb"
)


def read_incidents():
    """Read open reconciliation incidents from DuckDB."""

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"DuckDB database not found: {DB_PATH}"
        )

    connection = duckdb.connect(
        database=str(DB_PATH),
        read_only=True,
    )

    try:
        incidents = connection.execute("""
            SELECT *
            FROM main.fct_reconciliation_incidents
            ORDER BY
                CASE incident_severity
                    WHEN 'HIGH' THEN 1
                    WHEN 'MEDIUM' THEN 2
                    ELSE 3
                END,
                order_id
        """).df()

        return incidents

    finally:
        connection.close()


if __name__ == "__main__":
    df = read_incidents()

    print(f"Total incidents: {len(df)}")
    print()

    if df.empty:
        print("No reconciliation incidents found.")
    else:
        print(df.to_string(index=False))
