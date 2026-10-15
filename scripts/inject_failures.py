from pathlib import Path

import numpy as np
import pandas as pd


# -----------------------------
# Configuration
# -----------------------------

SEED = 100

NUM_DUPLICATE_PAYMENTS = 5
NUM_MISSING_PAYMENTS = 5
NUM_AMOUNT_MISMATCHES = 5
NUM_INVALID_CURRENCIES = 5
NUM_NULL_PAYMENT_IDS = 3
NUM_MISSING_SETTLEMENTS = 5


# -----------------------------
# Paths
# -----------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_DIR = PROJECT_ROOT / "data" / "raw"

TEST_DIR = PROJECT_ROOT / "data" / "test"

TEST_DIR.mkdir(parents=True, exist_ok=True)


# -----------------------------
# Load baseline datasets
# -----------------------------

orders = pd.read_csv(
    RAW_DIR / "orders" / "orders.csv"
)

payments = pd.read_csv(
    RAW_DIR / "payments" / "payments.csv"
)

refunds = pd.read_csv(
    RAW_DIR / "refunds" / "refunds.csv"
)

settlements = pd.read_csv(
    RAW_DIR / "settlements" / "settlements.csv"
)


# -----------------------------
# Reproducible random generator
# -----------------------------

rng = np.random.default_rng(SEED)


# =========================================================
# 1. DUPLICATE PAYMENTS
# =========================================================

duplicate_rows = payments.sample(
    n=NUM_DUPLICATE_PAYMENTS,
    random_state=SEED
).copy()

payments_with_duplicates = pd.concat(
    [payments, duplicate_rows],
    ignore_index=True
)


# =========================================================
# 2. MISSING PAYMENTS
# =========================================================

missing_payment_orders = orders[
    orders["order_status"] == "completed"
].sample(
    n=NUM_MISSING_PAYMENTS,
    random_state=SEED + 1
)

payments_without_some_orders = payments[
    ~payments["order_id"].isin(
        missing_payment_orders["order_id"]
    )
].copy()


# =========================================================
# 3. AMOUNT MISMATCHES
# =========================================================

payments_with_amount_mismatch = payments.copy()

mismatch_indices = rng.choice(
    payments_with_amount_mismatch.index,
    size=NUM_AMOUNT_MISMATCHES,
    replace=False
)

payments_with_amount_mismatch.loc[
    mismatch_indices,
    "amount"
] = (
    payments_with_amount_mismatch.loc[
        mismatch_indices,
        "amount"
    ]
    + 100
)


# =========================================================
# 4. INVALID CURRENCY
# =========================================================

payments_with_invalid_currency = payments.copy()

currency_indices = rng.choice(
    payments_with_invalid_currency.index,
    size=NUM_INVALID_CURRENCIES,
    replace=False
)

payments_with_invalid_currency.loc[
    currency_indices,
    "currency"
] = "XYZ"


# =========================================================
# 5. NULL PAYMENT IDENTIFIERS
# =========================================================

payments_with_null_ids = payments.copy()

null_id_indices = rng.choice(
    payments_with_null_ids.index,
    size=NUM_NULL_PAYMENT_IDS,
    replace=False
)

payments_with_null_ids.loc[
    null_id_indices,
    "payment_id"
] = pd.NA


# =========================================================
# 6. MISSING SETTLEMENTS
# =========================================================

missing_settlement_payments = payments.sample(
    n=NUM_MISSING_SETTLEMENTS,
    random_state=SEED + 2
)

settlements_without_some_payments = settlements[
    ~settlements["payment_id"].isin(
        missing_settlement_payments["payment_id"]
    )
].copy()


# =========================================================
# SAVE TEST DATASETS
# =========================================================

payments_with_duplicates.to_csv(
    TEST_DIR / "payments_duplicate.csv",
    index=False
)

payments_without_some_orders.to_csv(
    TEST_DIR / "payments_missing.csv",
    index=False
)

payments_with_amount_mismatch.to_csv(
    TEST_DIR / "payments_amount_mismatch.csv",
    index=False
)

payments_with_invalid_currency.to_csv(
    TEST_DIR / "payments_invalid_currency.csv",
    index=False
)

payments_with_null_ids.to_csv(
    TEST_DIR / "payments_null_id.csv",
    index=False
)

settlements_without_some_payments.to_csv(
    TEST_DIR / "settlements_missing.csv",
    index=False
)


# =========================================================
# SUMMARY
# =========================================================

print("Failure injection completed.\n")

print(
    "Duplicate payment rows added:",
    len(payments_with_duplicates) - len(payments)
)

print(
    "Missing payment records:",
    len(payments) - len(payments_without_some_orders)
)

print(
    "Amount mismatch records:",
    NUM_AMOUNT_MISMATCHES
)

print(
    "Invalid currency records:",
    NUM_INVALID_CURRENCIES
)

print(
    "Null payment IDs:",
    NUM_NULL_PAYMENT_IDS
)

print(
    "Missing settlement records:",
    len(settlements) - len(settlements_without_some_payments)
)

print("\nTest files saved to:")
print(TEST_DIR)