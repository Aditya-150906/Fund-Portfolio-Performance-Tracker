import pytest
import pandas as pd
import attribution
import rebalance
from attribution import (
    compute_monthly_attribution,
    monthly_sector_attribution,
    monthly_top_bottom_contributors,
    sector_contribution,
    stock_contribution,
    top_bottom_contributors,
)

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


def test_monthly_attribution_uses_each_month_and_handles_empty():
    weightage = pd.DataFrame({
        "Date": pd.to_datetime([
            "2025-01-31", "2025-01-31", "2025-02-28", "2025-02-28",
            "2025-03-31", "2025-03-31",
        ]),
        "ISIN": ["A", "B", "A", "B", "A", "B"],
        "Stock Name": ["A Corp", "B Corp"] * 3,
        "Current Weight": [60.0, 40.0] * 3,
    })
    calls = []

    def fake_monthly_contributions(fund_weightage, mapping, month_end, previous_month_end):
        calls.append((previous_month_end, month_end))
        return pd.DataFrame({
            "Stock Name": ["A Corp", "B Corp"],
            "ISIN": ["A", "B"],
            "Current Weight": [60.0, 40.0],
            "Stock Return": [0.10, -0.05],
            "Contribution": [6.0, -2.0],
            "Sector": ["Tech", None],
            "Return Status": ["Fetched (live)", "No Yahoo Ticker"],
        })

    original = attribution.compute_stock_contributions_for_month
    attribution.compute_stock_contributions_for_month = fake_monthly_contributions
    try:
        result = compute_monthly_attribution(weightage, pd.DataFrame(), top_n=1)
    finally:
        attribution.compute_stock_contributions_for_month = original

    assert list(result) == list(pd.to_datetime(["2025-02-28", "2025-03-31"]))
    assert calls == [
        (pd.Timestamp("2025-01-31"), pd.Timestamp("2025-02-28")),
        (pd.Timestamp("2025-02-28"), pd.Timestamp("2025-03-31")),
    ]
    assert result[pd.Timestamp("2025-02-28")]["total_contribution"] == pytest.approx(4.0)
    assert result[pd.Timestamp("2025-02-28")]["sector"].set_index("Sector").loc[
        "Unknown", "Contribution"
    ] == pytest.approx(-2.0)
    assert compute_monthly_attribution(pd.DataFrame(), pd.DataFrame()) == {}


def test_top_bottom_contributors_and_monthly_sector_table():
    contributions = pd.DataFrame({
        "Stock Name": ["Positive", "Small Positive", "Negative", "Small Negative"],
        "ISIN": ["P", "SP", "N", "SN"],
        "Current Weight": [40.0, 10.0, 30.0, 20.0],
        "Stock Return": [0.10, 0.01, -0.10, -0.01],
        "Contribution": [4.0, 0.1, -3.0, -0.2],
        "Sector": ["Tech", "Tech", "Unknown", "Finance"],
        "Return Status": ["Fetched (live)"] * 4,
    })
    top, bottom = top_bottom_contributors(contributions, n=1)
    assert top.iloc[0]["ISIN"] == "P"
    assert bottom.iloc[0]["ISIN"] == "N"

    monthly = {pd.Timestamp("2025-02-28"): {"data": contributions}}
    top_monthly, bottom_monthly = monthly_top_bottom_contributors(monthly, top_n=1)
    assert top_monthly.iloc[0]["Position"] == "Top"
    assert bottom_monthly.iloc[0]["Position"] == "Bottom"
    sector = monthly_sector_attribution({
        pd.Timestamp("2025-02-28"): {"sector": sector_contribution(contributions)},
    })
    assert set(sector["Sector"]) == {"Tech", "Unknown", "Finance"}
    assert sector["Weight"].sum() == pytest.approx(100.0)


def test_holdings_changes_classifies_snapshot_membership_and_weight_drift():
    previous = pd.DataFrame({
        "ISIN": ["A", "B", "C"],
        "Stock Name": ["A Corp", "B Corp", "C Corp"],
        "Current Weight": [50.0, 20.0, 10.0],
    })
    current = pd.DataFrame({
        "ISIN": ["A", "B", "D"],
        "Stock Name": ["A Corp", "B Corp", "D Corp"],
        "Current Weight": [60.0, 20.0, 10.0],
    })

    changes = rebalance.compute_holdings_changes(current, previous)
    by_isin = changes.set_index("ISIN")
    assert by_isin.loc["A", "Change Type"] == "Increased"
    assert by_isin.loc["A", "Weight Change"] == pytest.approx(10.0)
    assert by_isin.loc["B", "Change Type"] == "Unchanged"
    assert by_isin.loc["C", "Change Type"] == "Exited"
    assert by_isin.loc["C", "Current Weight"] == pytest.approx(0.0)
    assert by_isin.loc["D", "Change Type"] == "New"
    assert by_isin.loc["D", "Previous Weight"] == pytest.approx(0.0)


def test_sector_contribution_preserves_unknown_sector():
    result = sector_contribution(pd.DataFrame({
        "Sector": [None, ""],
        "Stock Name": ["A", "B"],
        "Current Weight": [50.0, 50.0],
        "Contribution": [1.0, -0.5],
    }))
    assert result.loc[result["Sector"] == "Unknown", "Contribution"].iloc[0] == pytest.approx(0.5)
