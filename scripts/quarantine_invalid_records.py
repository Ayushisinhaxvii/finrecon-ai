from pathlib import Path
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_DIR = PROJECT_ROOT / "data" / "raw"
TEST_DIR = PROJECT_ROOT / "data" / "test"
QUARANTINE_DIR = PROJECT_ROOT / "data" / "quarantine"

QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)


def save_quarantine(df, filename):
    """Save invalid records to the quarantine folder."""
    output_file = QUARANTINE_DIR / filename
    df.to_csv(output_file, index=False)

    print(f"  Quarantined records: {len(df)}")
    print(f"  Output: {output_file}")


# ============================================================
# 1. INVALID CURRENCY
# ============================================================

payments_invalid_currency = pd.read_csv(
    TEST_DIR / "payments_invalid_currency.csv"
)

invalid_currency = payments_invalid_currency[
    payments_invalid_currency["currency"] != "INR"
].copy()

print("\n1. INVALID CURRENCY")
save_quarantine(
    invalid_currency,
    "invalid_currency_payments.csv"
)


# ============================================================
# 2. NULL PAYMENT ID
# ============================================================

payments_null_id = pd.read_csv(
    TEST_DIR / "payments_null_id.csv"
)

null_payment_id = payments_null_id[
    payments_null_id["payment_id"].isna()
].copy()

print("\n2. NULL PAYMENT ID")
save_quarantine(
    null_payment_id,
    "null_payment_id.csv"
)


# ============================================================
# 3. DUPLICATE PAYMENT
# ============================================================

payments_duplicate = pd.read_csv(
    TEST_DIR / "payments_duplicate.csv"
)

duplicate_payment = payments_duplicate[
    payments_duplicate["payment_id"].duplicated(keep=False)
].copy()

print("\n3. DUPLICATE PAYMENT")
save_quarantine(
    duplicate_payment,
    "duplicate_payments.csv"
)


# ============================================================
# 4. PAYMENT AMOUNT MISMATCH
# ============================================================

payments_mismatch = pd.read_csv(
    TEST_DIR / "payments_amount_mismatch.csv"
)

orders = pd.read_csv(
    RAW_DIR / "orders" / "orders.csv"
)

payment_order_check = payments_mismatch.merge(
    orders[["order_id", "amount"]],
    on="order_id",
    how="left",
    suffixes=("_payment", "_order")
)

amount_mismatch = payment_order_check[
    payment_order_check["amount_payment"]
    != payment_order_check["amount_order"]
].copy()

print("\n4. PAYMENT AMOUNT MISMATCH")
save_quarantine(
    amount_mismatch,
    "payment_amount_mismatch.csv"
)


# ============================================================
# 5. MISSING PAYMENTS
# ============================================================

original_payments = pd.read_csv(
    RAW_DIR / "payments" / "payments.csv"
)

payments_missing = pd.read_csv(
    TEST_DIR / "payments_missing.csv"
)

missing_payment_ids = set(
    original_payments["payment_id"]
) - set(
    payments_missing["payment_id"]
)

missing_payments = original_payments[
    original_payments["payment_id"].isin(missing_payment_ids)
].copy()

print("\n5. MISSING PAYMENTS")
save_quarantine(
    missing_payments,
    "missing_payments.csv"
)


# ============================================================
# 6. MISSING SETTLEMENTS
# ============================================================

original_settlements = pd.read_csv(
    RAW_DIR / "settlements" / "settlements.csv"
)

settlements_missing = pd.read_csv(
    TEST_DIR / "settlements_missing.csv"
)

missing_settlement_payment_ids = set(
    original_settlements["payment_id"]
) - set(
    settlements_missing["payment_id"]
)

missing_settlements = original_settlements[
    original_settlements["payment_id"].isin(
        missing_settlement_payment_ids
    )
].copy()

print("\n6. MISSING SETTLEMENTS")
save_quarantine(
    missing_settlements,
    "missing_settlements.csv"
)


# ============================================================
# SUMMARY
# ============================================================

print("\n============================================")
print("QUARANTINE PROCESS COMPLETED")
print("============================================")

print(f"Invalid currency:     {len(invalid_currency)}")
print(f"Null payment IDs:     {len(null_payment_id)}")
print(f"Duplicate payments:   {len(duplicate_payment)}")
print(f"Amount mismatches:    {len(amount_mismatch)}")
print(f"Missing payments:     {len(missing_payments)}")
print(f"Missing settlements:  {len(missing_settlements)}")