
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

        # Use temporary folders instead of real project data.
        ingestion.RAW_DIR = test_root / "raw"
        ingestion.BRONZE_DIR = test_root / "bronze"
        ingestion.CHANGE_LOG_DIR = test_root / "change_log"
        ingestion.CHANGE_LOG_FILE = (
            ingestion.CHANGE_LOG_DIR / "change_log.csv"
        )

        raw_orders = ingestion.RAW_DIR / "orders"
        raw_orders.mkdir(parents=True)

        source_file = raw_orders / "orders.csv"
        bronze_file = (
            ingestion.BRONZE_DIR / "orders" / "orders.parquet"
        )

        # First source version.
        pd.DataFrame({
            "order_id": ["ORD001", "ORD002"],
            "amount": [100.0, 200.0],
        }).to_csv(source_file, index=False)

        ingestion.ingest_dataset("orders", "order_id")

        # Second source version: ORD001 changes; ORD003 is new.
        pd.DataFrame({
            "order_id": ["ORD001", "ORD002", "ORD003"],
            "amount": [120.0, 200.0, 300.0],
        }).to_csv(source_file, index=False)

        ingestion.ingest_dataset("orders", "order_id")

        # Check the change log.
        log_df = pd.read_csv(ingestion.CHANGE_LOG_FILE)

        assert len(log_df) == 1
        assert log_df.iloc[0]["order_id"] == "ORD001"
        assert log_df.iloc[0]["old_value"] == 100.0
        assert log_df.iloc[0]["new_value"] == 120.0

        # Check Bronze: original value remains; new order is added.
        bronze_df = pd.read_parquet(bronze_file)

        amount = bronze_df.loc[
            bronze_df["order_id"] == "ORD001", "amount"
        ].iloc[0]

        assert amount == 100.0
        assert len(bronze_df) == 3

        print("PASS: Changed amount was recorded in the change log.")
        print("PASS: Old value 100 and new value 120 were recorded.")
        print("PASS: Bronze retained the original amount of 100.")
        print("PASS: New order ORD003 was added.")
        print("\nChange log:")
        print(log_df.to_string(index=False))
        print("\nALL INGESTION CHANGE-LOG TESTS PASSED.")


if __name__ == "__main__":
    main()
