
from datetime import datetime, timezone
from pathlib import Path
import json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
METADATA_DIR = PROJECT_ROOT / "metadata"
LINEAGE_FILE = METADATA_DIR / "data_lineage.jsonl"


def record_lineage(
    dataset_name: str,
    source_layer: str,
    target_layer: str,
    source_path: str,
    target_path: str,
    rows_processed: int,
) -> dict:
    """Record how a dataset moves from one layer to another."""

    if rows_processed < 0:
        raise ValueError("rows_processed cannot be negative")

    record = {
        "dataset_name": dataset_name,
        "source_layer": source_layer,
        "target_layer": target_layer,
        "source_path": source_path,
        "target_path": target_path,
        "rows_processed": rows_processed,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }

    METADATA_DIR.mkdir(parents=True, exist_ok=True)

    with LINEAGE_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record) + "\n")

    return record


if __name__ == "__main__":
    record = record_lineage(
        dataset_name="payments",
        source_layer="Raw",
        target_layer="Bronze",
        source_path="data/raw/payments/payments.csv",
        target_path="data/bronze/payments/payments.parquet",
        rows_processed=800,
    )

    print("Data lineage recorded:")
    print(json.dumps(record, indent=2))
    print(f"\nSaved to: {LINEAGE_FILE}")
