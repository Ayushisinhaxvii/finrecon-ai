import pandas as pd
import pandera.pandas as pa


order_schema = pa.DataFrameSchema(
    {
        "order_id": pa.Column(
            str,
            nullable=False,
            unique=True,
        ),
        "customer_id": pa.Column(
            str,
            nullable=False,
        ),
        "amount": pa.Column(
            float,
            nullable=False,
            checks=pa.Check.gt(0),
        ),
        "currency": pa.Column(
            str,
            nullable=False,
            checks=pa.Check.isin(["INR"]),
        ),
        "order_timestamp": pa.Column(
            pa.DateTime,
            nullable=False,
        ),
        "order_status": pa.Column(
            str,
            nullable=False,
            checks=pa.Check.isin(
                ["completed", "cancelled", "pending"]
            ),
        ),
    },
    strict=True,
)


def validate_orders(df: pd.DataFrame) -> pd.DataFrame:
    """Validate orders against the order data contract."""
    return order_schema.validate(df)