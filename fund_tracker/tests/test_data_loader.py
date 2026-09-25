import pytest
import pandas as pd
from data_loader import _is_cash_row

def test_is_cash_row():
    df = pd.DataFrame({
        "ISIN": ["INE123", "CASH", "NA", None],
        "Stock Name": ["Apple", "CASH & EQUIVALENTS", "Net Cash", "Reliance"]
    })
    cash_mask = _is_cash_row(df)
    assert list(cash_mask) == [False, True, True, False]
