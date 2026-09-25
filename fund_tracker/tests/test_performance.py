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


def test_zero_volatility_and_zero_downside_are_handled_gracefully():
    zero_vol = pd.Series([0.0, 0.0, 0.0, 0.0])
    assert annualised_volatility(zero_vol) == 0.0
    assert np.isnan(sharpe_ratio(0.05, 0.0, 0.02))
    assert np.isnan(sortino_ratio(0.05, 0.0, 0.02))
    assert downside_deviation(zero_vol, risk_free_rate=0.0) == 0.0
