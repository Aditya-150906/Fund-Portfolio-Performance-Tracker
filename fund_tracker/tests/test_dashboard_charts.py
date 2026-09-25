import altair as alt
import pandas as pd
import plotly.graph_objects as go

import dashboard_charts


def test_dashboard_altair_chart_builders_return_charts():
    daily = pd.DataFrame({
        "Date": pd.date_range("2025-01-01", periods=2),
        "Portfolio NAV": [100.0, 101.0],
        "Benchmark NAV": [100.0, 100.5],
        "Rolling Volatility": [0.1, 0.11],
        "Drawdown": [0.0, -0.01],
    })

    assert isinstance(
        dashboard_charts.build_nav_vs_benchmark_chart(daily),
        alt.LayerChart,
    )
    assert isinstance(
        dashboard_charts.build_rolling_metric_chart(
            daily,
            "Rolling Volatility",
            "#D35400",
        ),
        alt.Chart,
    )
    assert isinstance(dashboard_charts.build_drawdown_chart(daily), alt.Chart)


def test_dashboard_plotly_chart_builders_return_figures():
    returns = pd.DataFrame({
        "Fund": ["Fund A", "Fund A"],
        "Metric": ["Absolute Return", "Benchmark Return"],
        "Return": [0.1, 0.08],
    })
    active = pd.DataFrame({"Fund": ["Fund A"], "Active Return": [0.02]})
    risk = pd.DataFrame({
        "Fund": ["Fund A", "Fund A"],
        "Metric": ["Tracking Error", "Max Drawdown"],
        "Risk": [0.1, -0.2],
    })

    assert isinstance(dashboard_charts.build_research_returns_chart(returns), go.Figure)
    assert isinstance(dashboard_charts.build_active_return_chart(active), go.Figure)
    assert isinstance(dashboard_charts.build_research_risk_chart(risk), go.Figure)


def test_growth_and_contributor_builders_handle_deterministic_data():
    daily = pd.DataFrame({
        "Date": pd.date_range("2025-01-01", periods=2),
        "Cumulative Portfolio Return": [0.0, 0.01],
        "Cumulative Benchmark Return": [0.0, 0.005],
    })
    contributors = pd.DataFrame({
        "Stock Name": ["A Corp"],
        "Contribution": [0.5],
    })

    growth = dashboard_charts.build_growth_chart(daily)
    assert list(growth.columns) == ["Portfolio", "Benchmark"]
    assert isinstance(dashboard_charts.build_contributor_chart(contributors, "#1F4E78"), alt.Chart)