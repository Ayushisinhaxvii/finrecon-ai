
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent

datasets = ["orders", "payments", "refunds", "settlements"]

for dataset in datasets:
    bronze_file = (
        PROJECT_ROOT / "data" / "bronze" / dataset
        / f"{dataset}.parquet"
    )
    silver_file = (
        PROJECT_ROOT / "data" / "silver" / dataset
        / f"{dataset}.parquet"
    )

    bronze_rows = len(pd.read_parquet(bronze_file))
    silver_rows = len(pd.read_parquet(silver_file))

    print(
        f"{dataset}: Bronze={bronze_rows} rows, "
        f"Silver={silver_rows} rows"
    )
