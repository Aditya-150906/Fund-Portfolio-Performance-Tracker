import pytest
import pandas as pd
from rebalance import compute_weight_drift

def test_compute_weight_drift(sample_holdings, sample_previous_holdings):
    df = compute_weight_drift(sample_holdings, sample_previous_holdings, threshold=3.0)
    # INE123: 50 -> 60 (drift +10), required True
    # INE456: 40 -> 35 (drift -5), required True
    # INE789: 10 -> 0 (drift -10), required True
    # CASH: 0 -> 5 (drift +5), required True
    assert len(df) == 4

    ine123 = df[df["ISIN"] == "INE123"].iloc[0]
    assert ine123["Drift"] == 10.0
    assert ine123["Rebalance Required"] == True

    cash = df[df["ISIN"] == "CASH"].iloc[0]
    assert cash["Previous Weight"] == 0.0
    assert cash["Drift"] == 5.0
