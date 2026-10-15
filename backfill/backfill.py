
import pandas as pd


def backfill_missing_day(
    source_df: pd.DataFrame,
    date_column: str,
    missing_date: str,
    primary_key: str,
    processed_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Reprocess missing historical records for one date.

    This function works with DataFrames in memory.
    It does not modify project Bronze or Silver files.
    """

    # 1. Validate required columns.
    required_columns = {date_column, primary_key}

    for name, df in [
        ("source_df", source_df),
        ("processed_df", processed_df),
    ]:
        missing_columns = required_columns - set(df.columns)

        if missing_columns:
            raise ValueError(
                f"{name} is missing required columns: "
                f"{sorted(missing_columns)}"
            )

    # 2. Validate the requested date.
    try:
        target_date = pd.Timestamp(missing_date).date()
    except (TypeError, ValueError):
        raise ValueError(
            f"Invalid backfill date: {missing_date}"
        ) from None

    if pd.isna(pd.Timestamp(missing_date)):
        raise ValueError(
            f"Invalid backfill date: {missing_date}"
        )

    # 3. Work on copies so input DataFrames remain unchanged.
    source = source_df.copy()
    processed = processed_df.copy()

    source[date_column] = pd.to_datetime(
        source[date_column],
        errors="coerce",
    )
    processed[date_column] = pd.to_datetime(
        processed[date_column],
        errors="coerce",
    )

    # 4. Reject invalid timestamps in the source.
    if source[date_column].isna().any():
        raise ValueError(
            f"Source contains invalid values in {date_column}."
        )

    # 5. Reject null or duplicate primary keys.
    if source[primary_key].isna().any():
        raise ValueError(
            f"Source contains null values in {primary_key}."
        )

    if source[primary_key].duplicated().any():
        raise ValueError(
            f"Source contains duplicate values in {primary_key}."
        )

    if processed[primary_key].isna().any():
        raise ValueError(
            f"Processed data contains null values in {primary_key}."
        )

    if processed[primary_key].duplicated().any():
        raise ValueError(
            f"Processed data contains duplicate values in {primary_key}."
        )

    if processed[date_column].isna().any():
        raise ValueError(
            f"Processed data contains invalid values in {date_column}."
        )

    # 6. Select records from the requested historical date.
    historical_records = source[
        source[date_column].dt.date == target_date
    ].copy()

    # 7. Keep only records not already processed.
    existing_ids = set(processed[primary_key])

    missing_records = historical_records[
        ~historical_records[primary_key].isin(existing_ids)
    ].copy()

    # 8. Combine records and validate uniqueness.
    updated_data = pd.concat(
        [processed, missing_records],
        ignore_index=True,
        sort=False,
    )

    if updated_data[primary_key].duplicated().any():
        raise ValueError(
            "Duplicate primary keys detected after backfill."
        )

    print(f"Backfill date: {target_date}")
    print(f"Historical records found: {len(historical_records)}")
    print(f"New records added: {len(missing_records)}")
    print(f"Total processed records: {len(updated_data)}")

    return updated_data


if __name__ == "__main__":
    # Synthetic example only: no project data files are modified.

    source_data = pd.DataFrame({
        "payment_id": ["PAY001", "PAY002", "PAY003"],
        "order_id": ["ORD001", "ORD002", "ORD003"],
        "amount": [100.0, 200.0, 300.0],
        "payment_timestamp": [
            "2026-09-21 10:00:00",
            "2026-09-22 11:00:00",
            "2026-09-23 12:00:00",
        ],
    })

    initially_processed = source_data[
        source_data["payment_timestamp"].str[:10] != "2026-09-22"
    ].copy()

    print("Before backfill:", len(initially_processed), "records")

    updated_data = backfill_missing_day(
        source_df=source_data,
        date_column="payment_timestamp",
        missing_date="2026-09-22",
        primary_key="payment_id",
        processed_df=initially_processed,
    )

    print("\nAfter backfill:", len(updated_data), "records")

    # Idempotency: repeating the same backfill adds no duplicates.
    repeated_data = backfill_missing_day(
        source_df=source_data,
        date_column="payment_timestamp",
        missing_date="2026-09-22",
        primary_key="payment_id",
        processed_df=updated_data,
    )

    assert len(repeated_data) == len(updated_data)
    assert repeated_data["payment_id"].is_unique

    print("\nBackfill demo passed.")
    print("Repeated backfill did not create duplicates.")
