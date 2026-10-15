
import duckdb
from pathlib import Path

root = Path.cwd()
database_paths = [
    root / "dev.duckdb",
    root / "dbt" / "finrecon" / "dev.duckdb",
]

for db_path in database_paths:
    print(f"\n{'=' * 70}")
    print(f"DATABASE: {db_path}")
    print(f"EXISTS: {db_path.exists()}")

    if not db_path.exists():
        continue

    con = duckdb.connect(str(db_path), read_only=True)
    try:
        rows = con.execute("""
            SELECT view_name, sql
            FROM duckdb_views()
            WHERE NOT internal
              AND view_name IN (
                  'stg_orders',
                  'stg_payments',
                  'stg_refunds',
                  'stg_settlements'
              )
            ORDER BY view_name
        """).fetchall()

        for name, sql in rows:
            print(f"\n{name}:")
            print(sql)
    finally:
        con.close()
