"""
dashboard_charts.py
-------------------
Chart construction helpers used only by the Streamlit dashboard.

These functions receive already-prepared DataFrames and return Altair or
Plotly chart objects. Financial calculations, data loading, and Yahoo Finance
access remain in their existing modules.
"""

import altair as alt
import pandas as pd
import plotly.express as px


def build_nav_vs_benchmark_chart(daily: pd.DataFrame):
    """Build the dual-axis NAV versus benchmark Altair chart."""
    df = (
        daily[
            [
                "Date",
                "Portfolio NAV",
                "Benchmark NAV",
            ]
        ]
        .dropna(
            subset=[
                "Portfolio NAV",
                "Benchmark NAV",
            ]
        )
        .drop_duplicates(
            subset=["Date"]
        )
        .sort_values("Date")
    )

    base = alt.Chart(df).encode(
        x=alt.X(
            "Date:T",
            title=None,
        )
    )

    port_line = base.mark_line(
        color="#1F4E78"
    ).encode(
        y=alt.Y(
            "Portfolio NAV:Q",
            axis=alt.Axis(
                title="Portfolio NAV",
                titleColor="#1F4E78",
            ),
        ),
        tooltip=[
            "Date:T",
            "Portfolio NAV:Q",
        ],
    )

    bench_line = base.mark_line(
        color="#C0392B",
        strokeDash=[4, 2],
    ).encode(
        y=alt.Y(
            "Benchmark NAV:Q",
            axis=alt.Axis(
                title="Benchmark NAV",
                titleColor="#C0392B",
            ),
        ),
        tooltip=[
            "Date:T",
            "Benchmark NAV:Q",
        ],
    )

    return alt.layer(
        port_line,
        bench_line,
    ).resolve_scale(
        y="independent"
    )


def build_rolling_metric_chart(daily: pd.DataFrame, metric: str, color: str):
    """Build a rolling-risk metric Altair line chart."""
    df = (
        daily[["Date", metric]]
        .dropna(subset=[metric])
        .drop_duplicates(subset=["Date"])
        .sort_values("Date")
    )
    base = alt.Chart(df).encode(x=alt.X("Date:T", title=None))
    return base.mark_line(color=color).encode(
        y=alt.Y(
            f"{metric}:Q",
            axis=alt.Axis(title=metric, titleColor=color),
        ),
        tooltip=["Date:T", f"{metric}:Q"],
    )


def build_drawdown_chart(daily: pd.DataFrame):
    """Build the drawdown Altair area chart."""
    df = (
        daily[["Date", "Drawdown"]]
        .dropna(subset=["Drawdown"])
        .drop_duplicates(subset=["Date"])
        .sort_values("Date")
    )
    base = alt.Chart(df).encode(x=alt.X("Date:T", title=None))
    return base.mark_area(color="#C0392B", opacity=0.5).encode(
        y=alt.Y(
            "Drawdown:Q",
            axis=alt.Axis(
                title="Drawdown",
                titleColor="#C0392B",
                format="%",
            ),
        ),
        tooltip=["Date:T", alt.Tooltip("Drawdown:Q", format=".2%")],
    )


def build_growth_chart(daily: pd.DataFrame) -> pd.DataFrame:
    """Prepare the existing Streamlit line-chart input for portfolio growth."""
    return (
        daily[
            [
                "Date",
                "Cumulative Portfolio Return",
                "Cumulative Benchmark Return",
            ]
        ]
        .dropna(
            subset=[
                "Cumulative Portfolio Return",
                "Cumulative Benchmark Return",
            ]
        )
        .drop_duplicates(
            subset=["Date"]
        )
        .sort_values("Date")
        .rename(
            columns={
                "Cumulative Portfolio Return": "Portfolio",
                "Cumulative Benchmark Return": "Benchmark",
            }
        )
        .set_index("Date")
    )


def build_research_returns_chart(return_chart_data: pd.DataFrame):
    """Build the existing portfolio-return versus benchmark Plotly chart."""
    fig = px.bar(
        return_chart_data,
        x="Fund",
        y="Return",
        color="Metric",
        barmode="group",
        title="Portfolio Return vs Benchmark",
        labels={
            "Return": "Return",
            "Fund": "Fund",
        },
    )
    fig.update_yaxes(tickformat=".1%")
    return fig


def build_active_return_chart(active_chart_data: pd.DataFrame):
    """Build the existing active-return-by-fund Plotly chart."""
    fig = px.bar(
        active_chart_data,
        x="Fund",
        y="Active Return",
        title="Active Return by Fund",
        labels={
            "Active Return": "Active Return",
            "Fund": "Fund",
        },
    )
    fig.update_yaxes(tickformat=".1%")
    return fig


def build_research_risk_chart(risk_chart_data: pd.DataFrame):
    """Build the existing tracking-error and drawdown Plotly chart."""
    fig = px.bar(
        risk_chart_data,
        x="Fund",
        y="Risk",
        color="Metric",
        barmode="group",
        title="Risk & Drawdown Comparison",
        labels={
            "Risk": "Percentage",
            "Fund": "Fund",
        },
    )
    fig.update_yaxes(tickformat=".1%")
    return fig


def build_monthly_contribution_chart(monthly_summary: pd.DataFrame):
    """Build the monthly portfolio-contribution Plotly chart."""
    return px.bar(
        monthly_summary,
        x="Month",
        y="Total Contribution",
        title="Monthly Portfolio Contribution",
        labels={"Total Contribution": "Contribution (pp)"},
    )


def build_sector_contribution_chart(sector_df: pd.DataFrame, month_label: str):
    """Build the selected-month sector-contribution Plotly chart."""
    return px.bar(
        sector_df,
        x="Sector",
        y="Contribution",
        title=f"Sector Contribution - {month_label}",
        labels={"Contribution": "Contribution (pp)"},
    )


def build_contributor_chart(df: pd.DataFrame, color: str):
    """Build the existing contributor Altair bar chart."""
    chart_df = df[
        [
            "Stock Name",
            "Contribution",
        ]
    ].copy()

    return (
        alt.Chart(chart_df)
        .mark_bar(color=color)
        .encode(
            x=alt.X(
                "Contribution:Q",
                title="Contribution (%)",
                axis=alt.Axis(format=".2f"),
            ),
            y=alt.Y(
                "Stock Name:N",
                sort="-x",
                title=None,
            ),
            tooltip=[
                "Stock Name",
                alt.Tooltip(
                    "Contribution:Q",
                    format="+.2f",
                    title="Contribution (%)",
                ),
            ],
        )
        .properties(height=32 * max(len(chart_df), 1))
    )