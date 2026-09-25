import pandas as pd

from dashboard_sections import (
    build_fundamental_display_frame,
    build_holdings_change_display_frame,
    build_monthly_attribution_summary,
    build_research_display_frame,
    build_research_return_chart_frame,
    build_research_risk_chart_frame,
    select_contributor_display_columns,
)


def test_research_display_and_chart_frames_preserve_existing_formatting():
    research_df = pd.DataFrame({
        "Fund": ["Fund A"],
        "Absolute Return": [0.10],
        "Benchmark Return": [0.08],
        "Active Return": [0.02],
        "CAGR": [0.09],
        "Sharpe Ratio": [1.25],
        "Information Ratio": [0.75],
        "Tracking Error": [0.04],
        "Max Drawdown": [-0.12],
    })

    display = build_research_display_frame(research_df)
    assert display.loc[0, "Absolute Return"] == "10.00%"
    assert display.loc[0, "Sharpe Ratio"] == "1.25"

    returns = build_research_return_chart_frame(research_df)
    assert returns["Metric"].tolist() == [
        "Absolute Return",
        "Benchmark Return",
    ]
    risk = build_research_risk_chart_frame(research_df)
    assert risk["Metric"].tolist() == ["Tracking Error", "Max Drawdown"]


def test_fundamental_display_frame_merges_and_formats_cash_exclusion():
    detail_weightage = pd.DataFrame({
        "ISIN": ["A", "CASH"],
        "Fund Name": ["Fund A", "Fund A"],
        "Stock Name": ["A Corp", "Cash"],
        "Current Weight": [25.0, 75.0],
        "Is Cash": [False, True],
    })
    mapping = pd.DataFrame({
        "ISIN": ["A", "CASH"],
        "Yahoo Ticker": ["A.NS", ""],
    })
    fundamental_data = pd.DataFrame({
        "ISIN": ["A", "CASH"],
        "Yahoo Ticker": ["A.NS", ""],
        "Market Cap": [1_000_000_000_000, None],
        "PE Ratio": [20.0, None],
        "PB Ratio": [3.0, None],
        "ROE": [0.15, None],
        "Dividend Yield": [0.02, None],
        "Debt to Equity": [40.0, None],
    })

    display = build_fundamental_display_frame(
        detail_weightage,
        mapping,
        fundamental_data,
    )

    assert len(display) == 1
    assert display.loc[0, "Company"] == "A Corp"
    assert display.loc[0, "Weight"] == "25.00%"
    assert display.loc[0, "Market Cap"] == "1.00 T"
    assert display.loc[0, "ROE"] == "15.00%"


def test_attribution_and_holdings_display_helpers_preserve_rows_and_audit_columns():
    monthly = build_monthly_attribution_summary({
        pd.Timestamp("2025-02-28"): {
            "total_contribution": 1.5,
            "window_start": pd.Timestamp("2025-01-31"),
            "window_end": pd.Timestamp("2025-02-28"),
        },
    })
    assert monthly.loc[0, "Total Contribution"] == 1.5
    assert monthly.loc[0, "Window Start"] == pd.Timestamp("2025-01-31")

    contributor = pd.DataFrame({
        "Stock Name": ["A Corp"],
        "ISIN": ["A"],
        "Current Weight": [25.0],
        "Stock Return": [0.10],
        "Contribution": [2.5],
        "Return Status": ["Fetched (live)"],
        "Return Start Date": ["2025-01-31"],
    })
    columns = select_contributor_display_columns(contributor)
    assert "Return Status" in columns
    assert "Return Start Date" in columns

    changes = pd.DataFrame({
        "ISIN": ["A"],
        "Change Type": ["Increased"],
        "Weight Change": [5.0],
    })
    displayed_changes = build_holdings_change_display_frame(changes)
    assert displayed_changes.equals(changes)