
from pathlib import Path
import sys
import tempfile

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import ingestion.raw_to_bronze as ingestion


def main():
    with tempfile.TemporaryDirectory() as temp_dir:
        test_root = Path(temp_dir)

        # All test outputs stay in temporary folders.
        raw_dir = test_root / "raw"
        bronze_dir = test_root / "bronze"
        change_log_dir = test_root / "change_log"
        change_log_file = change_log_dir / "change_log.csv"

        orders_dir = raw_dir / "orders"
        orders_dir.mkdir(parents=True)

        raw_file = orders_dir / "orders.csv"
        bronze_file = bronze_dir / "orders" / "orders.parquet"

        # Redirect ALL ingestion outputs to temporary folders.
        ingestion.RAW_DIR = raw_dir
        ingestion.BRONZE_DIR = bronze_dir
        ingestion.CHANGE_LOG_DIR = change_log_dir
        ingestion.CHANGE_LOG_FILE = change_log_file

        # Test 1: Initial load.
        initial_data = pd.DataFrame({
            "order_id": [
                "ORD_TEST_001",
                "ORD_TEST_002",
                "ORD_TEST_003",
            ],
            "amount": [100.0, 200.0, 300.0],
        })

        initial_data.to_csv(raw_file, index=False)

        ingestion.ingest_dataset("orders", "order_id")

        bronze_df = pd.read_parquet(bronze_file)

        assert len(bronze_df) == 3
        print("PASS: Initial load contains 3 records.")

        # Test 2: Add one new order.
        updated_data = pd.concat(
            [
                initial_data,
                pd.DataFrame({
                    "order_id": ["ORD_TEST_004"],
                    "amount": [400.0],
                }),
            ],
            ignore_index=True,
        )

        updated_data.to_csv(raw_file, index=False)

        ingestion.ingest_dataset("orders", "order_id")

        bronze_df = pd.read_parquet(bronze_file)

        assert len(bronze_df) == 4
        assert bronze_df["order_id"].nunique() == 4
        assert "ORD_TEST_004" in bronze_df["order_id"].values

        print("PASS: New order added; Bronze contains 4 unique orders.")

        # Test 3: Repeated ingestion must not create duplicates.
        ingestion.ingest_dataset("orders", "order_id")

        bronze_df = pd.read_parquet(bronze_file)

        assert len(bronze_df) == 4
        assert bronze_df["order_id"].is_unique

        print("PASS: Repeated ingestion created no duplicates.")

        # Test 4: Change an existing source record.
        updated_data = pd.read_csv(raw_file)

        updated_data.loc[
            updated_data["order_id"] == "ORD_TEST_001",
            "amount",
        ] = 999.0

        updated_data.to_csv(raw_file, index=False)

        ingestion.ingest_dataset("orders", "order_id")

        bronze_df = pd.read_parquet(bronze_file)

        stored_amount = bronze_df.loc[
            bronze_df["order_id"] == "ORD_TEST_001",
            "amount",
        ].iloc[0]

        print(f"Existing Bronze amount: {stored_amount}")

        # Bronze should preserve the original value.
        assert stored_amount == 100.0

        print("PASS: Existing Bronze record was not overwritten.")

        # Verify the change log was written to the temporary folder.
        assert change_log_file.exists()

        log_df = pd.read_csv(change_log_file)

        matching_change = log_df[
            (log_df["dataset"] == "orders")
            & (log_df["order_id"] == "ORD_TEST_001")
            & (log_df["column"] == "amount")
            & (log_df["old_value"] == 100.0)
            & (log_df["new_value"] == 999.0)
        ]

        assert len(matching_change) == 1

        print("PASS: Change recorded in the temporary change log.")
        print("PASS: Real project change log was not used.")

    print("\nALL INCREMENTAL INGESTION TESTS PASSED.")


if __name__ == "__main__":
    main()
