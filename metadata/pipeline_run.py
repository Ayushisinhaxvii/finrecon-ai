
from datetime import datetime, timezone
from pathlib import Path
import json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
METADATA_DIR = PROJECT_ROOT / "metadata"
RUN_LOG_FILE = METADATA_DIR / "pipeline_runs.jsonl"


def record_pipeline_run(
    pipeline_name: str,
    dataset_name: str,
    status: str,
    rows_processed: int,
    message: str = "",
) -> dict:
    """
    Record one pipeline run as a JSON line.

    JSONL means each line is a separate JSON record.
    """

    if status not in {"SUCCESS", "FAILED"}:
        raise ValueError("status must be SUCCESS or FAILED")

    if rows_processed < 0:
        raise ValueError("rows_processed cannot be negative")

    run_record = {
        "pipeline_name": pipeline_name,
        "dataset_name": dataset_name,
        "status": status,
        "rows_processed": rows_processed,
        "message": message,
        "run_timestamp": datetime.now(timezone.utc).isoformat(),
    }

    METADATA_DIR.mkdir(parents=True, exist_ok=True)

    with RUN_LOG_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(run_record) + "\n")

    return run_record


if __name__ == "__main__":
    record = record_pipeline_run(
        pipeline_name="raw_to_bronze",
        dataset_name="payments",
        status="SUCCESS",
        rows_processed=800,
        message="Metadata logging test",
    )

    print("Pipeline run recorded:")
    print(json.dumps(record, indent=2))
    print(f"\nSaved to: {RUN_LOG_FILE}")
