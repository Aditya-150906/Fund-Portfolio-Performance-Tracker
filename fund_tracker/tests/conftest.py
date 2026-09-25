import pytest
import pandas as pd
import numpy as np

@pytest.fixture
def sample_nav_data():
    dates = pd.date_range("2020-01-01", periods=10, freq="B")
    return pd.DataFrame({
        "Date": dates,
        "Fund Code": "TEST01",
        "Portfolio NAV": [100.0, 101.0, 102.0, 101.5, 103.0, 104.0, 103.5, 105.0, 106.0, 107.0],
        "Benchmark NAV": [100.0, 100.5, 101.0, 100.0, 101.5, 102.0, 101.0, 102.5, 103.0, 104.0]
    })

@pytest.fixture
def sample_holdings():
    return pd.DataFrame({
        "ISIN": ["INE123", "INE456", "CASH"],
        "Stock Name": ["A", "B", "CASH"],
        "Current Weight": [60.0, 35.0, 5.0],
        "Fund Code": "TEST01"
    })

@pytest.fixture
def sample_previous_holdings():
    return pd.DataFrame({
        "ISIN": ["INE123", "INE456", "INE789"],
        "Stock Name": ["A", "B", "C"],
        "Current Weight": [50.0, 40.0, 10.0]
    })
