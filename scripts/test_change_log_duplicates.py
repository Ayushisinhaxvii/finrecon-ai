
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
        root = Path(temp_dir)

        ingestion.RAW_DIR = root / "raw"
        ingestion.BRONZE_DIR = root / "bronze"
        ingestion.CHANGE_LOG_DIR = root / "change_log"
        ingestion.CHANGE_LOG_FILE = (
            ingestion.CHANGE_LOG_DIR / "change_log.csv"
        )

        raw_orders = ingestion.RAW_DIR / "orders"
        raw_orders.mkdir(parents=True)

        source_file = raw_orders / "orders.csv"

        # Initial source version.
        pd.DataFrame({
            "order_id": ["ORD001"],
            "amount": [100.0],
        }).to_csv(source_file, index=False)

        ingestion.ingest_dataset("orders", "order_id")

        # Corrected source version.
        pd.DataFrame({
            "order_id": ["ORD001"],
            "amount": [120.0],
        }).to_csv(source_file, index=False)

        # Process the same correction twice.
        ingestion.ingest_dataset("orders", "order_id")
        ingestion.ingest_dataset("orders", "order_id")

        log_df = pd.read_csv(ingestion.CHANGE_LOG_FILE)

        assert len(log_df) == 1
        assert log_df.iloc[0]["old_value"] == 100.0
        assert log_df.iloc[0]["new_value"] == 120.0

        print("PASS: Repeated ingestion did not duplicate the log entry.")
        print("PASS: The original and corrected values are preserved.")
        print("\nALL DUPLICATE-LOG TESTS PASSED.")


if __name__ == "__main__":
    main()
