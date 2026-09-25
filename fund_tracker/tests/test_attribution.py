import pytest
import pandas as pd
from attribution import stock_contribution, sector_contribution

def test_stock_contribution():
    df = pd.DataFrame({
        "ISIN": ["A", "B"],
        "Stock Name": ["A Corp", "B Corp"],
        "Current Weight": [60.0, 40.0],
        "Sector": ["Tech", "Fin"],
        "Stock Return": [0.10, -0.05]
    })
    res = stock_contribution(df)
    assert "Contribution" in res.columns
    assert res[res["ISIN"] == "A"].iloc[0]["Contribution"] == pytest.approx(0.06)
    assert res[res["ISIN"] == "B"].iloc[0]["Contribution"] == pytest.approx(-0.02)

def test_sector_contribution():
    df = pd.DataFrame({
        "Sector": ["Tech", "Tech", "Fin"],
        "Stock Name": ["A Corp", "B Corp", "C Corp"],
        "Current Weight": [50.0, 10.0, 40.0],
        "Contribution": [5.0, -1.0, 4.0]
    })
    res = sector_contribution(df)
    tech = res[res["Sector"] == "Tech"].iloc[0]
    assert tech["Weight"] == 60.0
    assert tech["Contribution"] == 4.0
