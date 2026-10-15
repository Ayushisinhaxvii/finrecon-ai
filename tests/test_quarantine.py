from pathlib import Path
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
QUARANTINE_DIR = PROJECT_ROOT / "data" / "quarantine"


def test_invalid_currency_quarantine():
    df = pd.read_csv(
        QUARANTINE_DIR / "invalid_currency_payments.csv"
    )

    assert len(df) == 5
    assert (df["currency"] != "INR").all()


def test_null_payment_id_quarantine():
    df = pd.read_csv(
        QUARANTINE_DIR / "null_payment_id.csv"
    )

    assert len(df) == 3
    assert df["payment_id"].isna().all()


def test_duplicate_payment_quarantine():
    df = pd.read_csv(
        QUARANTINE_DIR / "duplicate_payments.csv"
    )

    assert len(df) == 10
    assert df["payment_id"].duplicated(keep=False).all()


def test_amount_mismatch_quarantine():
    df = pd.read_csv(
        QUARANTINE_DIR / "payment_amount_mismatch.csv"
    )

    assert len(df) == 5
    assert (df["amount_payment"] != df["amount_order"]).all()


def test_missing_payment_quarantine():
    df = pd.read_csv(
        QUARANTINE_DIR / "missing_payments.csv"
    )

    assert len(df) == 5


def test_missing_settlement_quarantine():
    df = pd.read_csv(
        QUARANTINE_DIR / "missing_settlements.csv"
    )

    assert len(df) == 5