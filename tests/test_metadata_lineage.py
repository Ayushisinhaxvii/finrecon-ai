
import json

import pytest

from metadata import pipeline_run
from metadata import data_lineage


def test_pipeline_run_metadata_is_saved(tmp_path, monkeypatch):
    log_file = tmp_path / "pipeline_runs.jsonl"

    monkeypatch.setattr(pipeline_run, "METADATA_DIR", tmp_path)
    monkeypatch.setattr(pipeline_run, "RUN_LOG_FILE", log_file)

    record = pipeline_run.record_pipeline_run(
        pipeline_name="raw_to_bronze",
        dataset_name="payments",
        status="SUCCESS",
        rows_processed=800,
        message="Automated test",
    )

    saved_record = json.loads(log_file.read_text(encoding="utf-8"))

    assert record["pipeline_name"] == "raw_to_bronze"
    assert record["dataset_name"] == "payments"
    assert record["status"] == "SUCCESS"
    assert record["rows_processed"] == 800
    assert saved_record == record
    assert "run_timestamp" in saved_record


def test_pipeline_run_rejects_invalid_status():
    with pytest.raises(ValueError):
        pipeline_run.record_pipeline_run(
            pipeline_name="raw_to_bronze",
            dataset_name="payments",
            status="UNKNOWN",
            rows_processed=10,
        )


def test_pipeline_run_rejects_negative_row_count():
    with pytest.raises(ValueError):
        pipeline_run.record_pipeline_run(
            pipeline_name="raw_to_bronze",
            dataset_name="payments",
            status="SUCCESS",
            rows_processed=-1,
        )


def test_data_lineage_is_saved(tmp_path, monkeypatch):
    lineage_file = tmp_path / "data_lineage.jsonl"

    monkeypatch.setattr(data_lineage, "METADATA_DIR", tmp_path)
    monkeypatch.setattr(data_lineage, "LINEAGE_FILE", lineage_file)

    record = data_lineage.record_lineage(
        dataset_name="payments",
        source_layer="Raw",
        target_layer="Bronze",
        source_path="data/raw/payments/payments.csv",
        target_path="data/bronze/payments/payments.parquet",
        rows_processed=800,
    )

    saved_record = json.loads(lineage_file.read_text(encoding="utf-8"))

    assert saved_record == record
    assert saved_record["source_layer"] == "Raw"
    assert saved_record["target_layer"] == "Bronze"
    assert saved_record["rows_processed"] == 800
    assert "recorded_at" in saved_record


def test_data_lineage_rejects_negative_row_count():
    with pytest.raises(ValueError):
        data_lineage.record_lineage(
            dataset_name="payments",
            source_layer="Raw",
            target_layer="Bronze",
            source_path="raw.csv",
            target_path="bronze.parquet",
            rows_processed=-1,
        )
