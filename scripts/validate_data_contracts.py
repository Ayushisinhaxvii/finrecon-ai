
from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from quality.order_contract import validate_orders
from quality.payment_contract import validate_payments
from quality.refund_contract import validate_refunds
from quality.settlement_contract import validate_settlements


RAW_DIR = PROJECT_ROOT / "data" / "raw"


def main():
    datasets = [
        ("orders", validate_orders),
        ("payments", validate_payments),
        ("refunds", validate_refunds),
        ("settlements", validate_settlements),
    ]

    failures = []

    print("DATA CONTRACT VALIDATION")
    print("Raw datasets will only be read, not modified.")

    for dataset_name, validator in datasets:
        file_path = RAW_DIR / dataset_name / f"{dataset_name}.csv"

        print(f"\nValidating: {dataset_name}")

        try:
            df = pd.read_csv(file_path)

            # Convert timestamp columns into datetime values.
            timestamp_columns = [
                column for column in df.columns
                if "timestamp" in column or column == "settlement_date"
            ]

            for column in timestamp_columns:
                df[column] = pd.to_datetime(
                    df[column],
                    errors="raise",
                )

            validator(df)

            print(f"PASS: {dataset_name} contract is valid.")
            print(f"Rows checked: {len(df)}")

        except Exception as error:
            failures.append(dataset_name)
            print(f"FAIL: {dataset_name} contract validation failed.")
            print(f"Reason: {error}")

    print("\n================================")
    print("VALIDATION SUMMARY")
    print("================================")
    print(f"Datasets checked: {len(datasets)}")
    print(f"Passed: {len(datasets) - len(failures)}")
    print(f"Failed: {len(failures)}")

    if failures:
        print("Failed datasets:", ", ".join(failures))
        raise SystemExit(1)

    print("\nALL DATA CONTRACTS PASSED.")


if __name__ == "__main__":
    main()
