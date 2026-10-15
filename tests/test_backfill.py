
import pandas as pd
import pytest

from backfill.backfill import backfill_missing_day


@pytest.fixture
def source_data():
    return pd.DataFrame({
        "payment_id": ["PAY001", "PAY002", "PAY003"],
        "order_id": ["ORD001", "ORD002", "ORD003"],
        "amount": [100.0, 200.0, 300.0],
        "payment_timestamp": [
            "2026-09-21 10:00:00",
            "2026-09-22 11:00:00",
            "2026-09-23 12:00:00",
        ],
    })


@pytest.fixture
def processed_data(source_data):
    # Simulate a missed day: September 22 was not processed.
    return source_data[
        source_data["payment_timestamp"].str[:10] != "2026-09-22"
    ].copy()


def test_backfill_adds_missing_historical_record(
    source_data, processed_data
):
    result = backfill_missing_day(
        source_df=source_data,
        date_column="payment_timestamp",
        missing_date="2026-09-22",
        primary_key="payment_id",
        processed_df=processed_data,
    )

    assert len(result) == 3
    assert "PAY002" in result["payment_id"].values


def test_repeated_backfill_does_not_create_duplicates(
    source_data, processed_data
):
    first_result = backfill_missing_day(
        source_df=source_data,
        date_column="payment_timestamp",
        missing_date="2026-09-22",
        primary_key="payment_id",
        processed_df=processed_data,
    )

    second_result = backfill_missing_day(
        source_df=source_data,
        date_column="payment_timestamp",
        missing_date="2026-09-22",
        primary_key="payment_id",
        processed_df=first_result,
    )

    assert len(second_result) == len(first_result)
    assert second_result["payment_id"].is_unique


def test_missing_required_column_is_rejected(
    source_data, processed_data
):
    invalid_source = source_data.drop(columns=["payment_timestamp"])

    with pytest.raises(ValueError, match="missing required columns"):
        backfill_missing_day(
            source_df=invalid_source,
            date_column="payment_timestamp",
            missing_date="2026-09-22",
            primary_key="payment_id",
            processed_df=processed_data,
        )


def test_invalid_date_is_rejected(source_data, processed_data):
    with pytest.raises(ValueError, match="Invalid backfill date"):
        backfill_missing_day(
            source_df=source_data,
            date_column="payment_timestamp",
            missing_date="not-a-date",
            primary_key="payment_id",
            processed_df=processed_data,
        )


def test_duplicate_source_ids_are_rejected(
    source_data, processed_data
):
    invalid_source = pd.concat(
        [source_data, source_data.iloc[[0]]],
        ignore_index=True,
    )

    with pytest.raises(ValueError, match="duplicate values"):
        backfill_missing_day(
            source_df=invalid_source,
            date_column="payment_timestamp",
            missing_date="2026-09-22",
            primary_key="payment_id",
            processed_df=processed_data,
        )
