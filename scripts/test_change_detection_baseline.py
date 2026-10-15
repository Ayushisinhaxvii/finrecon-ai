
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
        raw_dir = test_root / "raw"
        bronze_dir = test_root / "bronze"

        orders_dir = raw_dir / "orders"
        orders_dir.mkdir(parents=True)

        raw_file = orders_dir / "orders.csv"
        bronze_file = bronze_dir / "orders" / "orders.parquet"

        # First version of the source data.
        original_data = pd.DataFrame({
            "order_id": ["ORD_TEST_001"],
            "amount": [100.0],
        })
        original_data.to_csv(raw_file, index=False)

        # Redirect ingestion to temporary folders.
        ingestion.RAW_DIR = raw_dir
        ingestion.BRONZE_DIR = bronze_dir

        # Load the original record into Bronze.
        ingestion.ingest_dataset("orders", "order_id")

        # Simulate the source providing a corrected record.
        corrected_data = pd.DataFrame({
            "order_id": ["ORD_TEST_001"],
            "amount": [120.0],
        })
        corrected_data.to_csv(raw_file, index=False)

        # Run the current ingestion logic again.
        ingestion.ingest_dataset("orders", "order_id")

        bronze_df = pd.read_parquet(bronze_file)
        bronze_amount = bronze_df.loc[
            bronze_df["order_id"] == "ORD_TEST_001",
            "amount",
        ].iloc[0]

        # Confirm the current limitation.
        assert bronze_amount == 100.0
        print("PASS: Existing Bronze amount remains 100.0.")
        print("CONFIRMED: Current ingestion does not detect changes.")

    print("\nCHANGE-DETECTION BASELINE TEST PASSED.")


if __name__ == "__main__":
    main()
