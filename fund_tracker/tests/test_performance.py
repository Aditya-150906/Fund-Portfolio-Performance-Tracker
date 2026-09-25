import pytest
import pandas as pd
import numpy as np
from performance import (
    add_daily_returns,
    annualised_return,
    annualised_volatility,
    cagr,
    downside_deviation,
    max_drawdown,
    benchmark_comparison,
    calculate_beta,
    jensens_alpha,
    rolling_sharpe,
    sharpe_ratio,
    sortino_ratio,
)
from research import (
    compare_funds_for_overlap,
    compute_holdings_overlap,
    compute_portfolio_change,
    effective_number_of_holdings,
    hhi,
    market_cap_allocation,
    number_of_holdings,
    sector_allocation,
    top_10_holding_weight,
    top_5_holding_weight,
)

def test_add_daily_returns(sample_nav_data):
    df = add_daily_returns(sample_nav_data)
    assert "Portfolio Return" in df.columns
    assert "Benchmark Return" in df.columns
    assert pd.isna(df.iloc[0]["Portfolio Return"])

def test_cagr():
    dates = pd.date_range("2020-01-01", periods=253, freq="B")
    navs = pd.Series(np.linspace(100, 110, 253))
    res = cagr(navs, pd.Series(dates), min_years=0.5)
    assert res > 0.0

def test_max_drawdown():
    navs = pd.Series([100.0, 110.0, 99.0, 105.0])
    dd = max_drawdown(navs)
    assert np.isclose(dd, -0.1)

def test_benchmark_comparison():
    df = pd.DataFrame({
        "Portfolio NAV": [100.0, 101.0, 102.0, 101.0, 102.5],
        "Benchmark NAV": [100.0, 100.5, 101.0, 100.0, 101.0],
        "Portfolio Return": [0.0, 0.01, 0.0099, -0.0098, 0.0148],
        "Benchmark Return": [0.0, 0.005, 0.0049, -0.0099, 0.01],
        "Date": pd.date_range("2020-01-01", periods=5, freq="B")
    })
    res = benchmark_comparison(df)
    assert "Active Return" in res
    assert "Tracking Error" in res
    assert "Information Ratio" in res
    assert "Beta" in res
    assert "Jensen's Alpha" in res


def test_risk_metrics_edge_cases_and_formulae():
    portfolio = pd.Series([0.01, -0.02, 0.015, -0.01, 0.02, 0.005, -0.03, 0.01] * 3)
    benchmark = pd.Series([0.005, -0.01, 0.008, -0.015, 0.014, 0.006, -0.025, 0.015] * 3)

    vol = annualised_volatility(portfolio)
    assert np.isfinite(vol)
    assert vol > 0.0

    downside = downside_deviation(portfolio, risk_free_rate=0.0)
    assert np.isfinite(downside)
    assert downside >= 0.0

    sharpe = sharpe_ratio(0.10, vol, 0.02)
    assert np.isfinite(share := sharpe)
    assert share > 0.0

    sortino = sortino_ratio(0.10, downside, 0.02)
    assert np.isfinite(sortino)

    beta = calculate_beta(portfolio, benchmark)
    assert np.isfinite(beta)

    alpha = jensens_alpha(0.10, 0.08, beta, 0.02)
    assert np.isfinite(alpha)

    rolling = rolling_sharpe(portfolio, risk_free_rate=0.02, window=8)
    assert rolling.notna().any()


def test_short_history_risk_metrics_are_decoupled_from_cagr():
    rng = np.random.default_rng(42)
    daily_port = pd.Series(rng.normal(0.0008, 0.012, 180))
    daily_bench = pd.Series(rng.normal(0.0005, 0.010, 180))
    dates = pd.Series(pd.date_range("2025-01-01", periods=180, freq="B"))
    portfolio_nav = pd.Series(100.0 * np.cumprod(1 + daily_port))
    benchmark_nav = pd.Series(100.0 * np.cumprod(1 + daily_bench))

    assert np.isnan(cagr(portfolio_nav, dates))
    assert np.isnan(cagr(benchmark_nav, dates))

    port_ann = annualised_return(daily_port)
    bench_ann = annualised_return(daily_bench)
    vol = annualised_volatility(daily_port)
    down_dev = downside_deviation(daily_port, risk_free_rate=0.02)
    beta = calculate_beta(daily_port, daily_bench)

    assert np.isfinite(port_ann)
    assert np.isfinite(bench_ann)
    assert np.isfinite(vol)
    assert np.isfinite(down_dev)
    assert np.isfinite(beta)
    assert np.isfinite(sharpe_ratio(port_ann, vol, 0.02))
    assert np.isfinite(sortino_ratio(port_ann, down_dev, 0.02))
    assert np.isfinite(jensens_alpha(port_ann, bench_ann, beta, 0.02))


def test_portfolio_concentration_and_hhi():
    holdings = pd.DataFrame({
        "ISIN": ["A", "B", "C", "CASH"],
        "Current Weight": [50.0, 25.0, 25.0, 5.0],
        "Is Cash": [False, False, False, True],
    })
    assert top_5_holding_weight(holdings) == pytest.approx(1.0)
    assert top_10_holding_weight(holdings) == pytest.approx(1.0)
    assert number_of_holdings(holdings) == 3
    assert hhi(holdings) == pytest.approx(0.375)
    assert effective_number_of_holdings(holdings) == pytest.approx(2.6666666667)


def test_sector_allocation_and_market_cap_boundaries():
    holdings = pd.DataFrame({
        "ISIN": ["A", "B", "C", "D"],
        "Current Weight": [35.0, 30.0, 25.0, 10.0],
        "Sector": ["Technology", "Technology", "Financials", "Unknown"],
        "Market Cap": [25000000000, 5000000000, 1000000000, np.nan],
        "Is Cash": [False, False, False, False],
    })
    sector = sector_allocation(holdings)
    assert sector["Sector"].tolist() == ["Technology", "Financials", "Unknown"]
    assert sector["Weight"].sum() == pytest.approx(1.0)

    cap_alloc = market_cap_allocation(holdings)
    assert set(cap_alloc["Market Cap Bucket"]) == {"Large Cap", "Mid Cap", "Small Cap", "Unknown"}
    assert cap_alloc["Weight"].sum() == pytest.approx(1.0)


def test_holdings_overlap_and_weight_change_summary():
    a = pd.DataFrame({
        "ISIN": ["A", "B", "C"],
        "Current Weight": [40.0, 35.0, 25.0],
    })
    b = pd.DataFrame({
        "ISIN": ["B", "C", "D"],
        "Current Weight": [30.0, 40.0, 30.0],
    })
    overlap = compute_holdings_overlap(a, b)
    assert overlap["Common Holdings"] == 2
    assert overlap["Weight Overlap"] == pytest.approx(0.55)
    assert overlap["Holding Overlap Ratio"] > 0.0
    reverse_overlap = compute_holdings_overlap(b, a)
    assert reverse_overlap["Weight Overlap"] == pytest.approx(0.55)
    assert reverse_overlap["Holding Overlap Ratio"] == pytest.approx(
        overlap["Holding Overlap Ratio"]
    )

    prev = pd.DataFrame({
        "ISIN": ["A", "B", "D"],
        "Current Weight": [50.0, 30.0, 20.0],
    })
    change = compute_portfolio_change(a, prev)
    assert change["Total Absolute Weight Change"] > 0.0
    assert change["Turnover"] > 0.0
    assert change["Additions"] >= 0.0
    assert change["Removals"] >= 0.0


def test_fund_overlap_uses_latest_common_snapshot_date():
    dates = pd.to_datetime(["2025-01-31", "2025-02-28", "2025-03-31"])
    weightage = pd.DataFrame({
        "Fund Code": ["A", "A", "B", "B"],
        "Date": [dates[0], dates[2], dates[0], dates[1]],
        "ISIN": ["X", "X", "X", "X"],
        "Current Weight": [100.0, 100.0, 100.0, 100.0],
    })
    fund_data = type("FundData", (), {"weightage": weightage})()

    result = compare_funds_for_overlap(fund_data, ["A", "B"])

    assert bool(result.loc[0, "Available"])
    assert result.loc[0, "Snapshot Date"] == dates[0]


def test_fund_overlap_reports_no_common_snapshot_date():
    weightage = pd.DataFrame({
        "Fund Code": ["A", "B"],
        "Date": pd.to_datetime(["2025-01-31", "2025-02-28"]),
        "ISIN": ["X", "X"],
        "Current Weight": [100.0, 100.0],
    })
    fund_data = type("FundData", (), {"weightage": weightage})()

    result = compare_funds_for_overlap(fund_data, ["A", "B"])

    assert not bool(result.loc[0, "Available"])
    assert pd.isna(result.loc[0, "Snapshot Date"])
    assert "No common snapshot date" in result.loc[0, "Reason"]


def test_zero_volatility_and_zero_downside_are_handled_gracefully():
    zero_vol = pd.Series([0.0, 0.0, 0.0, 0.0])
    assert annualised_volatility(zero_vol) == 0.0
    assert np.isnan(sharpe_ratio(0.05, 0.0, 0.02))
    assert np.isnan(sortino_ratio(0.05, 0.0, 0.02))
    assert downside_deviation(zero_vol, risk_free_rate=0.0) == 0.0
