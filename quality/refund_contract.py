import pandas as pd
import pandera.pandas as pa


refund_schema = pa.DataFrameSchema(
    {
        "refund_id": pa.Column(
            str,
            nullable=False,
            unique=True,
        ),
        "payment_id": pa.Column(
            str,
            nullable=False,
        ),
        "order_id": pa.Column(
            str,
            nullable=False,
        ),
        "refund_amount": pa.Column(
            float,
            nullable=False,
            checks=pa.Check.gt(0),
        ),
        "refund_timestamp": pa.Column(
            pa.DateTime,
            nullable=False,
        ),
        "refund_status": pa.Column(
            str,
            nullable=False,
            checks=pa.Check.isin(["completed"]),
        ),
    },
    strict=True,
)


def validate_refunds(df: pd.DataFrame) -> pd.DataFrame:
    """Validate refunds against the refund data contract."""
    return refund_schema.validate(df)