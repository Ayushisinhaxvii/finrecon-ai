from pathlib import Path
import pandas as pd


# ============================================
# PROJECT PATHS
# ============================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

BRONZE_DIR = PROJECT_ROOT / "data" / "bronze"
SILVER_DIR = PROJECT_ROOT / "data" / "silver"


# ============================================
# DATASET CONFIGURATION
# ============================================

DATASET_CONFIG = {
    "orders": {
        "datetime_columns": ["order_timestamp"]
    },
    "payments": {
        "datetime_columns": ["payment_timestamp"]
    },
    "refunds": {
        "datetime_columns": ["refund_timestamp"]
    },
    "settlements": {
        "datetime_columns": ["settlement_date"]
    }
}


# ============================================
# TRANSFORM ONE DATASET
# ============================================

def transform_dataset(dataset_name, datetime_columns):

    input_file = (
        BRONZE_DIR
        / dataset_name
        / f"{dataset_name}.parquet"
    )

    output_folder = SILVER_DIR / dataset_name
    output_folder.mkdir(parents=True, exist_ok=True)

    output_file = (
        output_folder
        / f"{dataset_name}.parquet"
    )

    print(f"\nProcessing {dataset_name}...")

    # Read Bronze data
    df = pd.read_parquet(input_file)

    # Standardize column names
    df.columns = [
        column.strip().lower()
        for column in df.columns
    ]

    # Remove completely empty rows
    df = df.dropna(how="all")

    # Clean whitespace from string columns
    string_columns = df.select_dtypes(
        include=["object", "str"]
    ).columns

    for column in string_columns:
        df[column] = df[column].str.strip()

    # Convert date/time columns to datetime
    for column in datetime_columns:
        df[column] = pd.to_datetime(
            df[column],
            errors="coerce"
        )

    # Write Silver Parquet
    df.to_parquet(
        output_file,
        index=False
    )

    print(f"Rows: {len(df)}")
    print(f"Saved to: {output_file}")


# ============================================
# MAIN
# ============================================

if __name__ == "__main__":

    print("============================================")
    print("BRONZE → SILVER TRANSFORMATION")
    print("============================================")

    for dataset_name, config in DATASET_CONFIG.items():

        transform_dataset(
            dataset_name,
            config["datetime_columns"]
        )

    print("\nBronze → Silver transformation completed.")