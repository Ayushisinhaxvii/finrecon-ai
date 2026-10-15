import duckdb

# Create an in-memory DuckDB connection
con = duckdb.connect()

datasets = {
    "orders": "data/bronze/orders/orders.parquet",
    "payments": "data/bronze/payments/payments.parquet",
    "refunds": "data/bronze/refunds/refunds.parquet",
    "settlements": "data/bronze/settlements/settlements.parquet",
}

print("========== BRONZE VALIDATION ==========\n")

for name, file_path in datasets.items():

    print(f"--- {name.upper()} ---")

    # Count rows
    result = con.sql(
        f"""
        SELECT COUNT(*) AS total_rows
        FROM '{file_path}'
        """
    )

    print(result)

    # Show columns and data types
    result = con.sql(
        f"""
        DESCRIBE
        SELECT *
        FROM '{file_path}'
        """
    )

    print(result)

    print()

con.close()