
import pandas as pd


def process_new_refunds(
    incoming_refunds: pd.DataFrame,
    processed_refunds: pd.DataFrame,
) -> pd.DataFrame:
    """
    Add newly arrived refunds without duplicating existing refund IDs.
    This is a small test helper, not the production ingestion pipeline.
    """

    required_columns = {
        "refund_id",
        "payment_id",
        "order_id",
        "refund_amount",
        "refund_timestamp",
        "refund_status",
    }

    for name, df in [
        ("incoming_refunds", incoming_refunds),
        ("processed_refunds", processed_refunds),
    ]:
        missing = required_columns - set(df.columns)
        if missing:
            raise ValueError(
                f"{name} is missing required columns: {sorted(missing)}"
            )

    if incoming_refunds["refund_id"].isna().any():
        raise ValueError("Incoming refunds contain null refund IDs.")

    if incoming_refunds["refund_id"].duplicated().any():
        raise ValueError("Incoming refunds contain duplicate refund IDs.")

    if processed_refunds["refund_id"].isna().any():
        raise ValueError("Processed refunds contain null refund IDs.")

    if processed_refunds["refund_id"].duplicated().any():
        raise ValueError("Processed refunds contain duplicate refund IDs.")

    existing_ids = set(processed_refunds["refund_id"])

    new_refunds = incoming_refunds[
        ~incoming_refunds["refund_id"].isin(existing_ids)
    ]

    return pd.concat(
        [processed_refunds, new_refunds],
        ignore_index=True,
    )


def test_late_refund_is_processed_when_it_arrives():
    # First pipeline run: only the payment is known.
    initially_processed = pd.DataFrame(columns=[
        "refund_id",
        "payment_id",
        "order_id",
        "refund_amount",
        "refund_timestamp",
        "refund_status",
    ])

    # Refund arrives in a later run.
    late_refund = pd.DataFrame({
        "refund_id": ["REF_LATE_001"],
        "payment_id": ["PAY001"],
        "order_id": ["ORD001"],
        "refund_amount": [25.0],
        "refund_timestamp": ["2026-09-23 10:00:00"],
        "refund_status": ["completed"],
    })

    after_arrival = process_new_refunds(
        incoming_refunds=late_refund,
        processed_refunds=initially_processed,
    )

    assert len(after_arrival) == 1
    assert after_arrival["refund_id"].iloc[0] == "REF_LATE_001"

    print("PASS: Late refund was processed when it arrived.")

    # A repeated run must not add the same refund again.
    repeated_result = process_new_refunds(
        incoming_refunds=late_refund,
        processed_refunds=after_arrival,
    )

    assert len(repeated_result) == 1
    assert repeated_result["refund_id"].is_unique

    print("PASS: Repeated processing created no duplicate refunds.")


def test_duplicate_refunds_in_one_incoming_batch_are_rejected():
    duplicate_batch = pd.DataFrame({
        "refund_id": ["REF001", "REF001"],
        "payment_id": ["PAY001", "PAY001"],
        "order_id": ["ORD001", "ORD001"],
        "refund_amount": [25.0, 25.0],
        "refund_timestamp": [
            "2026-09-23 10:00:00",
            "2026-09-23 10:00:00",
        ],
        "refund_status": ["completed", "completed"],
    })

    empty_processed = duplicate_batch.iloc[0:0].copy()

    try:
        process_new_refunds(duplicate_batch, empty_processed)
    except ValueError as error:
        assert "duplicate refund IDs" in str(error)
        print("PASS: Duplicate refund IDs were rejected.")
    else:
        raise AssertionError("Duplicate incoming refunds were not rejected.")
