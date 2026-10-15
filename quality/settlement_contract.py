import pandas as pd
import pandera.pandas as pa


settlement_schema = pa.DataFrameSchema(
    {
        "settlement_id": pa.Column(
            str,
            nullable=False,
            unique=True,
        ),
        "payment_id": pa.Column(
            str,
            nullable=False,
        ),
        "settlement_amount": pa.Column(
            float,
            nullable=False,
            checks=pa.Check.gt(0),
        ),
        "settlement_date": pa.Column(
            pa.DateTime,
            nullable=False,
        ),
        "settlement_status": pa.Column(
            str,
            nullable=False,
            checks=pa.Check.isin(["settled"]),
        ),
    },
    strict=True,
)


def validate_settlements(df: pd.DataFrame) -> pd.DataFrame:
    """Validate settlements against the settlement data contract."""
    return settlement_schema.validate(df)