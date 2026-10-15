
import pandas as pd
import pytest

from ingestion import raw_to_bronze as ingestion


def test_additive_schema_change():
    old_df = pd.DataFrame({
        "payment_id": ["PAY001"],
        "order_id": ["ORD001"],
        "amount": [100.0],
    })

    new_df = pd.DataFrame({
        "payment_id": ["PAY001"],
        "order_id": ["ORD001"],
        "amount": [100.0],
        "currency": ["INR"],
    })

    added, removed = ingestion.validate_schema_compatibility(
        old_df,
        new_df,
        required_columns={"payment_id", "order_id", "amount"},
    )

    assert added == {"currency"}
    assert removed == set()


def test_breaking_schema_change():
    old_df = pd.DataFrame({
        "payment_id": ["PAY001"],
        "order_id": ["ORD001"],
        "amount": [100.0],
    })

    new_df = pd.DataFrame({
        "transaction_ref": ["PAY001"],
        "order_id": ["ORD001"],
        "amount": [100.0],
    })

    with pytest.raises(ValueError, match="Missing required columns"):
        ingestion.validate_schema_compatibility(
            old_df,
            new_df,
            required_columns={"payment_id", "order_id", "amount"},
        )


def test_unchanged_schema():
    df = pd.DataFrame({
        "payment_id": ["PAY001"],
        "order_id": ["ORD001"],
        "amount": [100.0],
    })

    added, removed = ingestion.validate_schema_compatibility(
        df,
        df.copy(),
        required_columns={"payment_id", "order_id", "amount"},
    )

    assert added == set()
    assert removed == set()


def test_ingestion_rejects_breaking_change_without_modifying_bronze(
    tmp_path, monkeypatch
):
    raw_dir = tmp_path / "raw"
    bronze_dir = tmp_path / "bronze"
    change_log_dir = tmp_path / "change_log"

    raw_payments = raw_dir / "payments"
    bronze_payments = bronze_dir / "payments"

    raw_payments.mkdir(parents=True)
    bronze_payments.mkdir(parents=True)

    # Existing Bronze data: this must remain unchanged.
    original_bronze = pd.DataFrame({
        "payment_id": ["PAY001"],
        "order_id": ["ORD001"],
        "amount": [100.0],
    })

    bronze_file = bronze_payments / "payments.parquet"
    original_bronze.to_parquet(bronze_file, index=False)

    # Simulate a breaking source change: payment_id was renamed.
    changed_source = pd.DataFrame({
        "transaction_ref": ["PAY001"],
        "order_id": ["ORD001"],
        "amount": [100.0],
    })

    changed_source.to_csv(
        raw_payments / "payments.csv",
        index=False,
    )

    # Redirect all paths to this test's temporary directory.
    monkeypatch.setattr(ingestion, "RAW_DIR", raw_dir)
    monkeypatch.setattr(ingestion, "BRONZE_DIR", bronze_dir)
    monkeypatch.setattr(ingestion, "CHANGE_LOG_DIR", change_log_dir)
    monkeypatch.setattr(
        ingestion,
        "CHANGE_LOG_FILE",
        change_log_dir / "change_log.csv",
    )

    with pytest.raises(ValueError, match="Breaking schema change"):
        ingestion.ingest_dataset("payments", "payment_id")

    # Confirm that the original Bronze data was not changed.
    after_failure = pd.read_parquet(bronze_file)

    pd.testing.assert_frame_equal(after_failure, original_bronze)

    # The failed run should not create a persistent change log.
    assert not (change_log_dir / "change_log.csv").exists()


def test_ingestion_persists_additive_schema_change(
    tmp_path, monkeypatch
):
    raw_dir = tmp_path / "raw"
    bronze_dir = tmp_path / "bronze"
    change_log_dir = tmp_path / "change_log"

    raw_payments = raw_dir / "payments"
    bronze_payments = bronze_dir / "payments"

    raw_payments.mkdir(parents=True)
    bronze_payments.mkdir(parents=True)

    original_bronze = pd.DataFrame({
        "payment_id": ["PAY001"],
        "order_id": ["ORD001"],
        "amount": [100.0],
    })

    bronze_file = bronze_payments / "payments.parquet"
    original_bronze.to_parquet(bronze_file, index=False)

    # Source adds a new column and one new payment.
    changed_source = pd.DataFrame({
        "payment_id": ["PAY001", "PAY002"],
        "order_id": ["ORD001", "ORD002"],
        "amount": [100.0, 200.0],
        "currency": ["INR", "INR"],
    })

    changed_source.to_csv(
        raw_payments / "payments.csv",
        index=False,
    )

    monkeypatch.setattr(ingestion, "RAW_DIR", raw_dir)
    monkeypatch.setattr(ingestion, "BRONZE_DIR", bronze_dir)
    monkeypatch.setattr(ingestion, "CHANGE_LOG_DIR", change_log_dir)
    monkeypatch.setattr(
        ingestion,
        "CHANGE_LOG_FILE",
        change_log_dir / "change_log.csv",
    )

    ingestion.ingest_dataset("payments", "payment_id")

    updated_bronze = pd.read_parquet(bronze_file)

    assert set(updated_bronze.columns) == {
        "payment_id", "order_id", "amount", "currency"
    }
    assert len(updated_bronze) == 2
    assert updated_bronze["payment_id"].is_unique

    currency_by_id = updated_bronze.set_index("payment_id")["currency"]
    assert currency_by_id["PAY001"] == "INR"
    assert currency_by_id["PAY002"] == "INR"
