from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SILVER_DIR = PROJECT_ROOT / "data" / "silver"

DATASET_CONFIG = {
    "orders": {
        "expected_rows": 1000,
        "datetime_columns": ["order_timestamp"]
    },
    "payments": {
        "expected_rows": 800,
        "datetime_columns": ["payment_timestamp"]
    },
    "refunds": {
        "expected_rows": 160,
        "datetime_columns": ["refund_timestamp"]
    },
    "settlements": {
        "expected_rows": 800,
        "datetime_columns": ["settlement_date"]
    },
}


def validate_dataset(dataset_name, config):
    file_path = SILVER_DIR / dataset_name / f"{dataset_name}.parquet"

    df = pd.read_parquet(file_path)

    print(f"\n========== {dataset_name.upper()} ==========")

    # 1. Check row count
    print("Rows:", len(df))
    print("Expected rows:", config["expected_rows"])

    if len(df) == config["expected_rows"]:
        print("Row count: PASS")
    else:
        print("Row count: FAIL")

    # 2. Check datetime columns
    for column in config["datetime_columns"]:
        print(f"{column} dtype:", df[column].dtype)

        if pd.api.types.is_datetime64_any_dtype(df[column]):
            print(f"{column}: PASS")
        else:
            print(f"{column}: FAIL")

    # 3. Check completely empty rows
    empty_rows = df.isna().all(axis=1).sum()

    print("Completely empty rows:", empty_rows)

    if empty_rows == 0:
        print("Empty-row check: PASS")
    else:
        print("Empty-row check: FAIL")


if __name__ == "__main__":

    print("============================================")
    print("SILVER LAYER VALIDATION")
    print("============================================")

    for dataset_name, config in DATASET_CONFIG.items():
        validate_dataset(dataset_name, config)

    print("\nSilver validation completed.")