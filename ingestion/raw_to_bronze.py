import sys
from pathlib import Path

import pandas as pd


# ============================================
# PROJECT PATHS
# ============================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

RAW_DIR = PROJECT_ROOT / "data" / "raw"
BRONZE_DIR = PROJECT_ROOT / "data" / "bronze"
CHANGE_LOG_DIR = PROJECT_ROOT / "data" / "change_log"
CHANGE_LOG_FILE = CHANGE_LOG_DIR / "change_log.csv"


# ============================================
# DATASETS + PRIMARY KEYS
# ============================================

DATASETS = {
    "orders": "order_id",
    "payments": "payment_id",
    "refunds": "refund_id",
    "settlements": "settlement_id",
}


# ============================================
# SCHEMA EVOLUTION
# ============================================

def detect_schema_changes(
    old_df: pd.DataFrame,
    new_df: pd.DataFrame,
):
    """Return column names added to or removed from the source."""

    old_columns = set(old_df.columns)
    new_columns = set(new_df.columns)

    added_columns = new_columns - old_columns
    removed_columns = old_columns - new_columns

    return added_columns, removed_columns


def validate_schema_compatibility(
    old_df: pd.DataFrame,
    new_df: pd.DataFrame,
    required_columns: set,
):
    """Reject source files that are missing required columns."""

    added_columns, removed_columns = detect_schema_changes(
        old_df,
        new_df,
    )

    missing_required_columns = (
        set(required_columns) - set(new_df.columns)
    )

    if missing_required_columns:
        raise ValueError(
            "Breaking schema change detected. "
            f"Missing required columns: "
            f"{sorted(missing_required_columns)}"
        )

    return added_columns, removed_columns


# ============================================
# CHANGE DETECTION
# ============================================

def detect_changes(
    old_df: pd.DataFrame,
    new_df: pd.DataFrame,
    primary_key: str,
    dataset_name: str,
) -> pd.DataFrame:
    """Find changed values for records already in Bronze."""

    common_columns = [
        column
        for column in old_df.columns
        if column != primary_key and column in new_df.columns
    ]

    comparison = old_df.merge(
        new_df,
        on=primary_key,
        how="inner",
        suffixes=("_old", "_new"),
    )

    changed_records = []

    for _, row in comparison.iterrows():
        for column in common_columns:
            old_value = row[f"{column}_old"]
            new_value = row[f"{column}_new"]

            if pd.isna(old_value) and pd.isna(new_value):
                continue

            if pd.isna(old_value) or pd.isna(new_value):
                changed = True
            else:
                changed = old_value != new_value

            if changed:
                changed_records.append(
                    {
                        "dataset": dataset_name,
                        primary_key: row[primary_key],
                        "column": column,
                        "old_value": old_value,
                        "new_value": new_value,
                    }
                )

    return pd.DataFrame(
        changed_records,
        columns=[
            "dataset",
            primary_key,
            "column",
            "old_value",
            "new_value",
        ],
    )


# ============================================
# CHANGE LOG
# ============================================

def save_change_log(changes: pd.DataFrame):
    """Save detected value changes to a persistent CSV log."""

    if changes.empty:
        return

    CHANGE_LOG_DIR.mkdir(parents=True, exist_ok=True)

    if CHANGE_LOG_FILE.exists():
        existing_log = pd.read_csv(CHANGE_LOG_FILE)

        combined_log = pd.concat(
            [existing_log, changes],
            ignore_index=True,
        ).drop_duplicates(
            subset=[
                "dataset",
                "column",
                "old_value",
                "new_value",
            ],
            keep="first",
        )
    else:
        combined_log = changes.copy()

    combined_log.to_csv(CHANGE_LOG_FILE, index=False)

    print(f"Change log saved: {CHANGE_LOG_FILE}")


# ============================================
# INCREMENTAL INGESTION + SCHEMA EVOLUTION
# ============================================

def ingest_dataset(dataset_name: str, primary_key: str):
    """
    Validate the source schema, detect changes, and add new records.

    Existing values are not overwritten by ordinary ingestion.
    Newly introduced columns are added to the Bronze schema.
    """

    source_file = RAW_DIR / dataset_name / f"{dataset_name}.csv"
    bronze_folder = BRONZE_DIR / dataset_name
    output_file = bronze_folder / f"{dataset_name}.parquet"

    print(f"\nProcessing: {dataset_name}")

    if not source_file.exists():
        raise FileNotFoundError(
            f"Source file not found: {source_file}"
        )

    raw_df = pd.read_csv(source_file)

    if primary_key not in raw_df.columns:
        raise ValueError(
            f"Breaking schema change detected for {dataset_name}. "
            f"Missing required primary key: {primary_key}"
        )

    if raw_df[primary_key].isna().any():
        raise ValueError(
            f"Null {primary_key} values found in {source_file}"
        )

    if raw_df[primary_key].duplicated().any():
        raise ValueError(
            f"Duplicate {primary_key} values found in {source_file}"
        )

    # Initial load
    if not output_file.exists():
        bronze_folder.mkdir(parents=True, exist_ok=True)
        raw_df.to_parquet(output_file, index=False)

        print(f"Initial load: {len(raw_df)} records.")
        print(f"Bronze saved: {output_file}")
        return

    # Read existing Bronze data
    bronze_df = pd.read_parquet(output_file)

    if primary_key not in bronze_df.columns:
        raise ValueError(
            f"Existing Bronze file is missing primary key "
            f"{primary_key}: {output_file}"
        )

    if bronze_df[primary_key].isna().any():
        raise ValueError(
            f"Null {primary_key} values found in {output_file}"
        )

    if bronze_df[primary_key].duplicated().any():
        raise ValueError(
            f"Duplicate {primary_key} values found in {output_file}"
        )

    # Existing Bronze columns define the compatibility baseline
    required_columns = set(bronze_df.columns)

    added_columns, removed_columns = validate_schema_compatibility(
        bronze_df,
        raw_df,
        required_columns=required_columns,
    )

    if removed_columns:
        print(
            "Removed columns detected:",
            sorted(removed_columns),
        )

    if added_columns:
        print(
            "Additive schema change detected. New columns:",
            sorted(added_columns),
        )
    else:
        print("No additive schema changes detected.")

    # Detect changes without overwriting existing values
    changes = detect_changes(
        bronze_df,
        raw_df,
        primary_key,
        dataset_name,
    )

    if not changes.empty:
        save_change_log(changes)
        print(f"Changed values detected: {len(changes)}")
    else:
        print("No changes detected in existing columns.")

    existing_ids = set(bronze_df[primary_key].dropna())

    new_records = raw_df[
        ~raw_df[primary_key].isin(existing_ids)
    ].copy()

    print(f"Existing Bronze records: {len(bronze_df)}")
    print(f"New records found: {len(new_records)}")

    # Prepare result in memory before writing
    updated_bronze = pd.concat(
        [bronze_df, new_records],
        ignore_index=True,
        sort=False,
    )

    # Populate newly added columns for existing records
    if added_columns and not bronze_df.empty:
        source_by_id = raw_df.set_index(primary_key)

        for column in added_columns:
            source_values = source_by_id[column]

            matching_ids = updated_bronze[primary_key].isin(
                source_values.index
            )

            updated_bronze.loc[matching_ids, column] = (
                updated_bronze.loc[
                    matching_ids, primary_key
                ].map(source_values)
            )

    if added_columns or not new_records.empty:
        updated_bronze.to_parquet(output_file, index=False)

        if added_columns:
            print("Bronze schema updated successfully.")

        if not new_records.empty:
            print(f"Added {len(new_records)} new records.")
    else:
        print("No new records or schema changes. Bronze unchanged.")


# ============================================
# MAIN + METADATA + LINEAGE
# ============================================

# ============================================
# MAIN + METADATA + LINEAGE
# ============================================

def main():
    from metadata.pipeline_run import record_pipeline_run
    from metadata.data_lineage import record_lineage

    print("============================================")
    print("INCREMENTAL RAW TO BRONZE INGESTION")
    print("WITH SCHEMA COMPATIBILITY CHECKS")
    print("============================================")

    for dataset_name, primary_key in DATASETS.items():
        source_file = RAW_DIR / dataset_name / f"{dataset_name}.csv"
        output_file = (
            BRONZE_DIR / dataset_name / f"{dataset_name}.parquet"
        )

        try:
            ingest_dataset(dataset_name, primary_key)

            bronze_df = pd.read_parquet(output_file)
            rows_processed = len(bronze_df)

            record_pipeline_run(
                pipeline_name="raw_to_bronze",
                dataset_name=dataset_name,
                status="SUCCESS",
                rows_processed=rows_processed,
                message="Ingestion completed successfully.",
            )

            record_lineage(
                dataset_name=dataset_name,
                source_layer="Raw",
                target_layer="Bronze",
                source_path=str(
                    source_file.relative_to(PROJECT_ROOT)
                ),
                target_path=str(
                    output_file.relative_to(PROJECT_ROOT)
                ),
                rows_processed=rows_processed,
            )

        except Exception as error:
            try:
                record_pipeline_run(
                    pipeline_name="raw_to_bronze",
                    dataset_name=dataset_name,
                    status="FAILED",
                    rows_processed=0,
                    message=f"{type(error).__name__}: {error}",
                )
            except Exception as logging_error:
                print(
                    "WARNING: Could not save failure metadata: "
                    f"{logging_error}"
                )

            raise

    print("\nIncremental ingestion completed.")


if __name__ == "__main__":
    main()
