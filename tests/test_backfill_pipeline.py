
from pathlib import Path
import tempfile

import pandas as pd

from backfill.backfill import backfill_missing_day
from scripts.transformations import bronze_to_silver as transformation


def test_backfill_reaches_bronze_and_silver():
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)

        raw_dir = root / "raw"
        bronze_dir = root / "bronze"
        silver_dir = root / "silver"

        raw_payments_dir = raw_dir / "payments"
        bronze_payments_dir = bronze_dir / "payments"
        raw_payments_dir.mkdir(parents=True)
        bronze_payments_dir.mkdir(parents=True)

        raw_file = raw_payments_dir / "payments.csv"
        bronze_file = bronze_payments_dir / "payments.parquet"

        # Complete source history contains three days.
        source_df = pd.DataFrame({
            "payment_id": ["PAY001", "PAY002", "PAY003"],
            "order_id": ["ORD001", "ORD002", "ORD003"],
            "amount": [100.0, 200.0, 300.0],
            "currency": ["INR", "INR", "INR"],
            "payment_status": ["paid", "paid", "paid"],
            "payment_timestamp": [
                "2026-09-21 10:00:00",
                "2026-09-22 11:00:00",
                "2026-09-23 12:00:00",
            ],
        })

        source_df.to_csv(raw_file, index=False)

        # Simulate Bronze having missed September 22.
        initial_bronze = source_df[
            source_df["payment_timestamp"].str[:10] != "2026-09-22"
        ].copy()

        initial_bronze.to_parquet(bronze_file, index=False)

        # Recover the missing date using the existing backfill function.
        recovered_bronze = backfill_missing_day(
            source_df=source_df,
            date_column="payment_timestamp",
            missing_date="2026-09-22",
            primary_key="payment_id",
            processed_df=pd.read_parquet(bronze_file),
        )

        recovered_bronze.to_parquet(bronze_file, index=False)

        # Verify Bronze contains all records without duplicate IDs.
        bronze_result = pd.read_parquet(bronze_file)

        assert len(bronze_result) == 3
        assert bronze_result["payment_id"].is_unique
        assert "PAY002" in bronze_result["payment_id"].values

        print("PASS: Backfill recovered the missing Bronze record.")

        # Redirect transformation paths to temporary directories.
        transformation.BRONZE_DIR = bronze_dir
        transformation.SILVER_DIR = silver_dir

        transformation.transform_dataset(
            "payments",
            ["payment_timestamp"],
        )

        silver_file = silver_dir / "payments" / "payments.parquet"
        silver_result = pd.read_parquet(silver_file)

        assert len(silver_result) == 3
        assert silver_result["payment_id"].is_unique
        assert "PAY002" in silver_result["payment_id"].values

        print("PASS: Recovered record reached Silver.")

        # Repeat backfill; no new records should be added.
        repeated_result = backfill_missing_day(
            source_df=source_df,
            date_column="payment_timestamp",
            missing_date="2026-09-22",
            primary_key="payment_id",
            processed_df=bronze_result,
        )

        assert len(repeated_result) == len(bronze_result)
        assert repeated_result["payment_id"].is_unique

        print("PASS: Repeated backfill created no duplicates.")

    print("\nBACKFILL PIPELINE INTEGRATION TEST PASSED.")


if __name__ == "__main__":
    test_backfill_reaches_bronze_and_silver()
