
from pathlib import Path
import sys
import tempfile

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import ingestion.raw_to_bronze as ingestion


DATASETS = {
    "orders": "order_id",
    "payments": "payment_id",
    "refunds": "refund_id",
    "settlements": "settlement_id",
}


def main():
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)

        # Redirect every output to temporary folders.
        ingestion.RAW_DIR = root / "raw"
        ingestion.BRONZE_DIR = root / "bronze"
        ingestion.CHANGE_LOG_DIR = root / "change_log"
        ingestion.CHANGE_LOG_FILE = (
            ingestion.CHANGE_LOG_DIR / "change_log.csv"
        )

        for dataset_name, primary_key in DATASETS.items():
            print(f"\nTesting: {dataset_name}")

            raw_folder = ingestion.RAW_DIR / dataset_name
            raw_folder.mkdir(parents=True)

            raw_file = raw_folder / f"{dataset_name}.csv"
            bronze_file = (
                ingestion.BRONZE_DIR
                / dataset_name
                / f"{dataset_name}.parquet"
            )

            test_id = f"TEST_{dataset_name.upper()}_001"

            # Create a small initial dataset.
            initial_data = pd.DataFrame({
                primary_key: [test_id],
                "amount": [100.0],
            })

            initial_data.to_csv(raw_file, index=False)

            # First ingestion creates Bronze.
            ingestion.ingest_dataset(dataset_name, primary_key)

            # Change the existing record's amount.
            corrected_data = pd.DataFrame({
                primary_key: [test_id],
                "amount": [120.0],
            })

            corrected_data.to_csv(raw_file, index=False)

            # Second ingestion should log the change.
            ingestion.ingest_dataset(dataset_name, primary_key)

            bronze_df = pd.read_parquet(bronze_file)

            # Bronze must preserve the original value.
            stored_amount = bronze_df.loc[
                bronze_df[primary_key] == test_id,
                "amount",
            ].iloc[0]

            assert stored_amount == 100.0

            log_df = pd.read_csv(ingestion.CHANGE_LOG_FILE)

            matching_change = log_df[
                (log_df["dataset"] == dataset_name)
                & (log_df[primary_key] == test_id)
                & (log_df["column"] == "amount")
                & (log_df["old_value"] == 100.0)
                & (log_df["new_value"] == 120.0)
            ]

            assert len(matching_change) == 1

            print(f"PASS: {dataset_name} change detected and logged.")
            print(f"PASS: {dataset_name} Bronze value remains 100.")

        print("\nALL FOUR DATASET TESTS PASSED.")
        print("All test outputs were kept in temporary folders.")


if __name__ == "__main__":
    main()
