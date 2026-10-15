
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_DIR = PROJECT_ROOT / "data" / "raw"
BRONZE_DIR = PROJECT_ROOT / "data" / "bronze"

DATASETS = {
    "orders": "order_id",
    "payments": "payment_id",
    "refunds": "refund_id",
    "settlements": "settlement_id",
}


def audit_dataset(dataset_name, primary_key):
    raw_file = RAW_DIR / dataset_name / f"{dataset_name}.csv"
    bronze_file = BRONZE_DIR / dataset_name / f"{dataset_name}.parquet"

    print(f"\nDataset: {dataset_name}")

    if not raw_file.exists():
        print("ERROR: Raw file is missing.")
        return

    if not bronze_file.exists():
        print("ERROR: Bronze file is missing.")
        return

    raw_df = pd.read_csv(raw_file)
    bronze_df = pd.read_parquet(bronze_file)

    print(f"Raw rows: {len(raw_df)}")
    print(f"Bronze rows: {len(bronze_df)}")

    if primary_key not in raw_df.columns:
        print(f"ERROR: {primary_key} missing from Raw.")
        return

    if primary_key not in bronze_df.columns:
        print(f"ERROR: {primary_key} missing from Bronze.")
        return

    if raw_df[primary_key].dropna().duplicated().any():
        print("WARNING: Duplicate IDs found in Raw.")

    if bronze_df[primary_key].dropna().duplicated().any():
        print("WARNING: Duplicate IDs found in Bronze.")

    raw_ids = set(raw_df[primary_key].dropna())
    bronze_ids = set(bronze_df[primary_key].dropna())

    print(f"IDs only in Raw: {len(raw_ids - bronze_ids)}")
    print(f"IDs only in Bronze: {len(bronze_ids - raw_ids)}")

    common_columns = [
        col for col in raw_df.columns
        if col != primary_key and col in bronze_df.columns
    ]

    raw_common = raw_df[raw_df[primary_key].isin(bronze_ids)]
    bronze_common = bronze_df[bronze_df[primary_key].isin(raw_ids)]

    merged = raw_common.merge(
        bronze_common,
        on=primary_key,
        how="inner",
        suffixes=("_raw", "_bronze"),
    )

    changed_count = 0

    for column in common_columns:
        raw_values = merged[f"{column}_raw"]
        bronze_values = merged[f"{column}_bronze"]

        equal = (
            raw_values.eq(bronze_values)
            | (raw_values.isna() & bronze_values.isna())
        )

        changed_count += int((~equal).sum())

    print(f"Potential differing field values: {changed_count}")


def main():
    print("READ-ONLY RAW VS BRONZE AUDIT")
    print("No files will be modified.")

    for dataset_name, primary_key in DATASETS.items():
        audit_dataset(dataset_name, primary_key)

    print("\nAudit completed.")


if __name__ == "__main__":
    main()
