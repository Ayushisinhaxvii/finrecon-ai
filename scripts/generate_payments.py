from pathlib import Path

import numpy as np
import pandas as pd


# -----------------------------
# Configuration
# -----------------------------

SEED = 43


# -----------------------------
# Paths
# -----------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

ORDERS_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "orders"
    / "orders.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "payments"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# -----------------------------
# Load orders
# -----------------------------

orders = pd.read_csv(
    ORDERS_FILE,
    parse_dates=["order_timestamp"]
)


# -----------------------------
# Validate required columns
# -----------------------------

required_columns = {
    "order_id",
    "amount",
    "currency",
    "order_timestamp",
    "order_status",
}

missing_columns = required_columns - set(orders.columns)

if missing_columns:
    raise ValueError(
        f"Missing required order columns: {missing_columns}"
    )


# -----------------------------
# Select completed orders
# -----------------------------

completed_orders = orders[
    orders["order_status"] == "completed"
].copy()


# -----------------------------
# Reproducible random generator
# -----------------------------

rng = np.random.default_rng(SEED)


# -----------------------------
# Generate payment IDs
# -----------------------------

payment_ids = [
    f"PAY{i:06d}"
    for i in range(1, len(completed_orders) + 1)
]


# -----------------------------
# Create payment DataFrame
# -----------------------------

payments = pd.DataFrame(
    {
        "payment_id": payment_ids,
        "order_id": completed_orders["order_id"].values,
        "amount": completed_orders["amount"].values,
        "currency": completed_orders["currency"].values,
        "payment_status": "paid",
        "payment_timestamp": (
            completed_orders["order_timestamp"]
            + pd.to_timedelta(
                rng.integers(1, 30, len(completed_orders)),
                unit="m"
            )
        ),
    }
)


# -----------------------------
# Save payments
# -----------------------------

output_file = OUTPUT_DIR / "payments.csv"

payments.to_csv(
    output_file,
    index=False
)


# -----------------------------
# Basic validation
# -----------------------------

print("Payments dataset generated successfully.")
print(f"Rows: {len(payments)}")
print(f"Columns: {list(payments.columns)}")
print(f"Saved to: {output_file}")

print("\nFirst 5 rows:")
print(payments.head())

print("\nPayment status distribution:")
print(payments["payment_status"].value_counts())