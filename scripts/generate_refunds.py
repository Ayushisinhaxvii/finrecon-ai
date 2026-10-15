from pathlib import Path

import numpy as np
import pandas as pd


# -----------------------------
# Configuration
# -----------------------------

SEED = 44
REFUND_RATE = 0.20


# -----------------------------
# Paths
# -----------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

PAYMENTS_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "payments"
    / "payments.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "refunds"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# -----------------------------
# Load payments
# -----------------------------

payments = pd.read_csv(
    PAYMENTS_FILE,
    parse_dates=["payment_timestamp"]
)


# -----------------------------
# Validate required columns
# -----------------------------

required_columns = {
    "payment_id",
    "order_id",
    "amount",
    "currency",
    "payment_status",
    "payment_timestamp",
}

missing_columns = required_columns - set(payments.columns)

if missing_columns:
    raise ValueError(
        f"Missing required payment columns: {missing_columns}"
    )


# -----------------------------
# Select payments eligible for refunds
# -----------------------------

rng = np.random.default_rng(SEED)

num_refunds = int(
    len(payments) * REFUND_RATE
)

refund_source = payments.sample(
    n=num_refunds,
    random_state=SEED
).copy()


# -----------------------------
# Generate refund IDs
# -----------------------------

refund_ids = [
    f"REF{i:06d}"
    for i in range(1, len(refund_source) + 1)
]


# -----------------------------
# Generate refund amounts
# -----------------------------

refund_amounts = np.round(
    refund_source["amount"].values
    * rng.uniform(0.10, 0.50, len(refund_source)),
    2
)


# -----------------------------
# Generate refund timestamps
# -----------------------------

refund_timestamps = (
    refund_source["payment_timestamp"]
    + pd.to_timedelta(
        rng.integers(1, 48, len(refund_source)),
        unit="h"
    )
)


# -----------------------------
# Create refund DataFrame
# -----------------------------

refunds = pd.DataFrame(
    {
        "refund_id": refund_ids,
        "payment_id": refund_source["payment_id"].values,
        "order_id": refund_source["order_id"].values,
        "refund_amount": refund_amounts,
        "refund_timestamp": refund_timestamps,
        "refund_status": "completed",
    }
)


# -----------------------------
# Save refunds
# -----------------------------

output_file = OUTPUT_DIR / "refunds.csv"

refunds.to_csv(
    output_file,
    index=False
)


# -----------------------------
# Basic validation
# -----------------------------

print("Refunds dataset generated successfully.")
print(f"Rows: {len(refunds)}")
print(f"Columns: {list(refunds.columns)}")
print(f"Saved to: {output_file}")

print("\nFirst 5 rows:")
print(refunds.head())

print("\nRefund status distribution:")
print(refunds["refund_status"].value_counts())