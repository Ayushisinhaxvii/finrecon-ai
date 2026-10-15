from pathlib import Path

import numpy as np
import pandas as pd


# -----------------------------
# Configuration
# -----------------------------

SEED = 45


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
    / "settlements"
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
# Select successful payments
# -----------------------------

successful_payments = payments[
    payments["payment_status"] == "paid"
].copy()


# -----------------------------
# Generate settlement IDs
# -----------------------------

settlement_ids = [
    f"SET{i:06d}"
    for i in range(1, len(successful_payments) + 1)
]


# -----------------------------
# Generate settlement dates
# -----------------------------

settlement_dates = (
    successful_payments["payment_timestamp"]
    + pd.to_timedelta(
        1,
        unit="D"
    )
)


# -----------------------------
# Create settlement DataFrame
# -----------------------------

settlements = pd.DataFrame(
    {
        "settlement_id": settlement_ids,
        "payment_id": successful_payments["payment_id"].values,
        "settlement_amount": successful_payments["amount"].values,
        "settlement_date": settlement_dates.dt.date,
        "settlement_status": "settled",
    }
)


# -----------------------------
# Save settlements
# -----------------------------

output_file = OUTPUT_DIR / "settlements.csv"

settlements.to_csv(
    output_file,
    index=False
)


# -----------------------------
# Basic validation
# -----------------------------

print("Settlements dataset generated successfully.")
print(f"Rows: {len(settlements)}")
print(f"Columns: {list(settlements.columns)}")
print(f"Saved to: {output_file}")

print("\nFirst 5 rows:")
print(settlements.head())

print("\nSettlement status distribution:")
print(settlements["settlement_status"].value_counts())