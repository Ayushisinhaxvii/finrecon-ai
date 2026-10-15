import pandas as pd
import pandera.pandas as pa


payment_schema = pa.DataFrameSchema(
    {
        "payment_id": pa.Column(
            str,
            nullable=False,
            unique=True,
        ),
        "order_id": pa.Column(
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
        "payment_status": pa.Column(
            str,
            nullable=False,
            checks=pa.Check.isin(["paid"]),
        ),
        "payment_timestamp": pa.Column(
            pa.DateTime,
            nullable=False,
        ),
    },
    strict=True,
)


def validate_payments(df: pd.DataFrame) -> pd.DataFrame:
    """Validate a payment DataFrame against the payment contract."""
    return payment_schema.validate(df)