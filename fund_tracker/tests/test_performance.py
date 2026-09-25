import pytest
import pandas as pd
import numpy as np
from performance import (
    add_daily_returns,
    cagr,
    max_drawdown,
    benchmark_comparison
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
