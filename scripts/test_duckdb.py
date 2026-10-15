import duckdb

# Create an in-memory DuckDB connection
con = duckdb.connect()

# Path to our Bronze Orders Parquet file
orders_file = "data/bronze/orders/orders.parquet"

# Count rows
result = con.sql(
    f"""
    SELECT COUNT(*) AS total_rows
    FROM '{orders_file}'
    """
)

print("Order row count:")
print(result)

# Show first 5 rows
result = con.sql(
    f"""
    SELECT *
    FROM '{orders_file}'
    LIMIT 5
    """
)

print("\nFirst 5 orders:")
print(result)

con.close()