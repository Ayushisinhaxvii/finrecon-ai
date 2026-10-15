
from pathlib import Path
import tempfile

import pandas as pd


def detect_changes(
    old_df: pd.DataFrame,
    new_df: pd.DataFrame,
    primary_key: str,
) -> pd.DataFrame:
    """Detect changed values in records that already exist."""

    comparison = old_df.merge(
        new_df,
        on=primary_key,
        how="inner",
        suffixes=("_old", "_new"),
    )

    changed_records = []

    for _, row in comparison.iterrows():
        for column in old_df.columns:
            if column == primary_key:
                continue

            old_value = row[f"{column}_old"]
            new_value = row[f"{column}_new"]

            if pd.isna(old_value) and pd.isna(new_value):
                continue

            if pd.isna(old_value) or pd.isna(new_value):
                changed = True
            else:
                changed = old_value != new_value

            if changed:
                changed_records.append({
                    primary_key: row[primary_key],
                    "column": column,
                    "old_value": old_value,
                    "new_value": new_value,
                })

    return pd.DataFrame(
        changed_records,
        columns=[
            primary_key,
            "column",
            "old_value",
            "new_value",
        ],
    )


def main():
    # All test files are temporary; real project data is untouched.
    with tempfile.TemporaryDirectory() as temp_dir:
        change_log_file = Path(temp_dir) / "change_log.csv"

        old_data = pd.DataFrame({
            "order_id": ["ORD001", "ORD002"],
            "amount": [100.0, 200.0],
            "order_status": ["completed", "pending"],
        })

        new_data = pd.DataFrame({
            "order_id": ["ORD001", "ORD002", "ORD003"],
            "amount": [120.0, 200.0, 300.0],
            "order_status": ["completed", "pending", "completed"],
        })

        changes = detect_changes(
            old_data,
            new_data,
            primary_key="order_id",
        )

        changes.to_csv(change_log_file, index=False)

        assert len(changes) == 1
        assert changes.iloc[0]["order_id"] == "ORD001"
        assert changes.iloc[0]["column"] == "amount"
        assert changes.iloc[0]["old_value"] == 100.0
        assert changes.iloc[0]["new_value"] == 120.0

        print("PASS: ORD001 amount change detected.")
        print("PASS: Old value 100.0 recorded.")
        print("PASS: New value 120.0 recorded.")
        print("PASS: Unchanged ORD002 was not flagged.")
        print("PASS: New ORD003 was not classified as a change.")

        print("\nDetected changes:")
        print(changes.to_string(index=False))

    print("\nALL CHANGE-DETECTION TESTS PASSED.")


if __name__ == "__main__":
    main()
