from pathlib import Path

import numpy as np
import pandas as pd


# -----------------------------
# Configuration
# -----------------------------

NUM_ORDERS = 1000
SEED = 42


# -----------------------------
# Paths
# -----------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "data" / "raw" / "orders"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# -----------------------------
# Reproducibility
# -----------------------------

rng = np.random.default_rng(SEED)


# -----------------------------
# Generate IDs
# -----------------------------

order_ids = [
    f"ORD{i:06d}"
    for i in range(1, NUM_ORDERS + 1)
]

customer_ids = [
    f"CUST{rng.integers(1, 501):04d}"
    for _ in range(NUM_ORDERS)
]


# -----------------------------
# Generate amounts
# -----------------------------

amounts = np.round(
    rng.uniform(100, 10000, NUM_ORDERS),
    2
)


# -----------------------------
# Generate currencies
# -----------------------------

currencies = rng.choice(
    ["INR"],
    size=NUM_ORDERS
)


# -----------------------------
# Generate timestamps
# -----------------------------

timestamps = pd.date_range(
    start="2026-09-01",
    periods=NUM_ORDERS,
    freq="15min"
)


# -----------------------------
# Generate order statuses
# -----------------------------

statuses = rng.choice(
    ["completed", "pending", "cancelled"],
    size=NUM_ORDERS,
    p=[0.80, 0.10, 0.10]
)


# -----------------------------
# Create DataFrame
# -----------------------------

orders = pd.DataFrame(
    {
        "order_id": order_ids,
        "customer_id": customer_ids,
        "amount": amounts,
        "currency": currencies,
        "order_timestamp": timestamps,
        "order_status": statuses,
    }
)


# -----------------------------
# Save dataset
# -----------------------------

output_file = OUTPUT_DIR / "orders.csv"

orders.to_csv(
    output_file,
    index=False
)


# -----------------------------
# Basic validation
# -----------------------------

print("Orders dataset generated successfully.")
print(f"Rows: {len(orders)}")
print(f"Columns: {list(orders.columns)}")
print(f"Saved to: {output_file}")

print("\nFirst 5 rows:")
print(orders.head())

print("\nOrder status distribution:")
print(orders["order_status"].value_counts())