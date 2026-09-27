"""
dashboard_charts.py
-------------------
Unified, theme-aware chart builders for Altair and Plotly.
Provides crisp, institutional financial styling.
"""

import altair as alt
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


_CHART_THEME = {
    "surface": "#0E131C",
    "background": "#080B10",
    "text": "#E6EDF3",
    "muted": "#7D8B9F",
    "border": "#1B2433",
    "grid": "#141B26",
    "primary": "#388BFD",
    "benchmark": "#F85149",
    "positive": "#2EA043",
    "negative": "#F85149",
    "warning": "#D29922",
    "palette": ["#388BFD", "#2EA043", "#A371F7", "#D29922", "#F0883E", "#58A6FF", "#3FB950"],
}


def set_chart_theme(tokens: dict) -> None:
    """Set the active visual theme used across all chart builders."""
    _CHART_THEME.update({
        "surface": tokens.get("surface", "#0E131C"),
        "background": tokens.get("background", "#080B10"),
        "text": tokens.get("text", "#E6EDF3"),
        "muted": tokens.get("text_muted", "#7D8B9F"),
        "border": tokens.get("border", "#1B2433"),
        "grid": tokens.get("border_subtle", "#141B26"),
        "primary": tokens.get("accent", "#388BFD"),
        "benchmark": tokens.get("negative", "#F85149"),
        "positive": tokens.get("positive", "#2EA043"),
        "negative": tokens.get("negative", "#F85149"),
        "warning": tokens.get("warning", "#D29922"),
    })


def _style_plotly_figure(fig, height: int = 340):
    """Apply terminal typography, subtle gridlines, and clean margins to Plotly figures."""
    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            family="Inter, -apple-system, BlinkMacSystemFont, sans-serif",
            color=_CHART_THEME["text"],
            size=11,
        ),
        title=dict(
            font=dict(
                family="JetBrains Mono, monospace",
                color=_CHART_THEME["text"],
                size=12,
            ),
            x=0.01,
            xanchor="left",
        ),
        legend=dict(
            font=dict(color=_CHART_THEME["muted"], size=10, family="JetBrains Mono, monospace"),
            bgcolor="rgba(0,0,0,0)",
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        margin=dict(l=40, r=20, t=36, b=30),
        hoverlabel=dict(
            bgcolor=_CHART_THEME["surface"],
            font_size=11,
            font_family="JetBrains Mono, monospace",
            font_color=_CHART_THEME["text"],
            bordercolor=_CHART_THEME["border"],
        ),
    )
    fig.update_xaxes(
        color=_CHART_THEME["muted"],
        title_font=dict(color=_CHART_THEME["muted"], size=10, family="JetBrains Mono, monospace"),
        tickfont=dict(color=_CHART_THEME["muted"], size=9, family="JetBrains Mono, monospace"),
        gridcolor=_CHART_THEME["grid"],
        linecolor=_CHART_THEME["border"],
        zerolinecolor=_CHART_THEME["border"],
        showgrid=True,
    )
    fig.update_yaxes(
        color=_CHART_THEME["muted"],
        title_font=dict(color=_CHART_THEME["muted"], size=10, family="JetBrains Mono, monospace"),
        tickfont=dict(color=_CHART_THEME["muted"], size=9, family="JetBrains Mono, monospace"),
        gridcolor=_CHART_THEME["grid"],
        linecolor=_CHART_THEME["border"],
        zerolinecolor=_CHART_THEME["border"],
        showgrid=True,
    )
    return fig


def build_nav_vs_benchmark_chart(daily: pd.DataFrame) -> alt.LayerChart:
    """Build dual-axis NAV vs Benchmark chart in Altair."""
    df = (
        daily[["Date", "Portfolio NAV", "Benchmark NAV"]]
        .dropna(subset=["Portfolio NAV", "Benchmark NAV"])
        .drop_duplicates(subset=["Date"])
        .sort_values("Date")
    )

    base = alt.Chart(df).encode(
        x=alt.X("Date:T", title=None, axis=alt.Axis(
            gridColor=_CHART_THEME["grid"],
            labelColor=_CHART_THEME["muted"],
            labelFont="JetBrains Mono",
            labelFontSize=10,
        ))
    )

    port_line = base.mark_line(
        color=_CHART_THEME["primary"],
        strokeWidth=2.0,
    ).encode(
        y=alt.Y(
            "Portfolio NAV:Q",
            axis=alt.Axis(
                title="Portfolio NAV (₹)",
                titleColor=_CHART_THEME["primary"],
                labelColor=_CHART_THEME["primary"],
                gridColor=_CHART_THEME["grid"],
                labelFont="JetBrains Mono",
                titleFont="JetBrains Mono",
                titleFontSize=10,
                labelFontSize=10,
            ),
        ),
        tooltip=[
            alt.Tooltip("Date:T", format="%d %b %Y"),
            alt.Tooltip("Portfolio NAV:Q", format=",.2f", title="Portfolio (₹)"),
        ],
    )

    bench_line = base.mark_line(
        color=_CHART_THEME["benchmark"],
        strokeDash=[3, 3],
        strokeWidth=1.5,
    ).encode(
        y=alt.Y(
            "Benchmark NAV:Q",
            axis=alt.Axis(
                title="Benchmark NAV (₹)",
                titleColor=_CHART_THEME["benchmark"],
                labelColor=_CHART_THEME["benchmark"],
                grid=False,
                labelFont="JetBrains Mono",
                titleFont="JetBrains Mono",
                titleFontSize=10,
                labelFontSize=10,
            ),
        ),
        tooltip=[
            alt.Tooltip("Date:T", format="%d %b %Y"),
            alt.Tooltip("Benchmark NAV:Q", format=",.2f", title="Benchmark (₹)"),
        ],
    )

    return alt.layer(port_line, bench_line).resolve_scale(
        y="independent"
    ).properties(background="transparent")


def build_rolling_metric_chart(daily: pd.DataFrame, metric: str, color: str = None) -> alt.Chart:
    """Build rolling metric chart in Altair."""
    df = (
        daily[["Date", metric]]
        .dropna(subset=[metric])
        .drop_duplicates(subset=["Date"])
        .sort_values("Date")
    )
    metric_color = color or _CHART_THEME["primary"]

    return alt.Chart(df).mark_line(color=metric_color, strokeWidth=1.8).encode(
        x=alt.X("Date:T", title=None, axis=alt.Axis(
            gridColor=_CHART_THEME["grid"],
            labelColor=_CHART_THEME["muted"],
            labelFont="JetBrains Mono",
            labelFontSize=10,
        )),
        y=alt.Y(
            f"{metric}:Q",
            axis=alt.Axis(
                title=metric,
                titleColor=_CHART_THEME["text"],
                labelColor=_CHART_THEME["muted"],
                gridColor=_CHART_THEME["grid"],
                labelFont="JetBrains Mono",
                titleFont="JetBrains Mono",
                titleFontSize=10,
                labelFontSize=10,
            ),
        ),
        tooltip=[
            alt.Tooltip("Date:T", format="%d %b %Y"),
            alt.Tooltip(f"{metric}:Q", format=".2f"),
        ],
    ).properties(background="transparent")


def build_drawdown_chart(daily: pd.DataFrame) -> alt.Chart:
    """Build underwater drawdown area chart in Altair."""
    df = (
        daily[["Date", "Drawdown"]]
        .dropna(subset=["Drawdown"])
        .drop_duplicates(subset=["Date"])
        .sort_values("Date")
    )

    return alt.Chart(df).mark_area(
        color=_CHART_THEME["negative"],
        opacity=0.25,
        line={"color": _CHART_THEME["negative"], "strokeWidth": 1.5},
    ).encode(
        x=alt.X("Date:T", title=None, axis=alt.Axis(
            gridColor=_CHART_THEME["grid"],
            labelColor=_CHART_THEME["muted"],
            labelFont="JetBrains Mono",
            labelFontSize=10,
        )),
        y=alt.Y(
            "Drawdown:Q",
            axis=alt.Axis(
                title="Drawdown",
                titleColor=_CHART_THEME["text"],
                labelColor=_CHART_THEME["muted"],
                gridColor=_CHART_THEME["grid"],
                format="%",
                labelFont="JetBrains Mono",
                titleFont="JetBrains Mono",
                titleFontSize=10,
                labelFontSize=10,
            ),
        ),
        tooltip=[
            alt.Tooltip("Date:T", format="%d %b %Y"),
            alt.Tooltip("Drawdown:Q", format=".2%"),
        ],
    ).properties(background="transparent")


def build_growth_chart(daily: pd.DataFrame) -> pd.DataFrame:
    """Prepare cumulative growth data for plotting."""
    return (
        daily[["Date", "Cumulative Portfolio Return", "Cumulative Benchmark Return"]]
        .dropna(subset=["Cumulative Portfolio Return", "Cumulative Benchmark Return"])
        .drop_duplicates(subset=["Date"])
        .sort_values("Date")
        .rename(columns={
            "Cumulative Portfolio Return": "Portfolio",
            "Cumulative Benchmark Return": "Benchmark",
        })
        .set_index("Date")
    )


def build_growth_plotly_chart(daily: pd.DataFrame) -> go.Figure:
    """Build interactive Cumulative Growth (% return) chart."""
    df = (
        daily[["Date", "Cumulative Portfolio Return", "Cumulative Benchmark Return"]]
        .dropna(subset=["Cumulative Portfolio Return", "Cumulative Benchmark Return"])
        .drop_duplicates(subset=["Date"])
        .sort_values("Date")
    )

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["Date"],
            y=df["Cumulative Portfolio Return"],
            name="Portfolio",
            line=dict(color=_CHART_THEME["primary"], width=2.0),
            hovertemplate="<b>Portfolio:</b> %{y:+.2%}<extra></extra>",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df["Date"],
            y=df["Cumulative Benchmark Return"],
            name="Benchmark",
            line=dict(color=_CHART_THEME["benchmark"], width=1.5, dash="dot"),
            hovertemplate="<b>Benchmark:</b> %{y:+.2%}<extra></extra>",
        )
    )

    fig.update_yaxes(tickformat="+.1%")
    return _style_plotly_figure(fig, height=320)


def build_sector_allocation_donut_chart(sector_df: pd.DataFrame):
    """Build modern Plotly donut chart for Sector Allocation."""
    if sector_df.empty:
        return None

    df = sector_df.copy()
    if (df["Weight"] > 1).any():
        df["Weight"] = df["Weight"] / 100.0

    fig = px.pie(
        df,
        values="Weight",
        names="Sector",
        hole=0.6,
        color_discrete_sequence=_CHART_THEME["palette"],
    )
    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        hoverinfo="label+percent",
        marker=dict(line=dict(color=_CHART_THEME["surface"], width=1.2)),
    )
    fig.update_layout(
        showlegend=False,
        margin=dict(l=10, r=10, t=10, b=10),
    )
    return _style_plotly_figure(fig, height=280)


def build_market_cap_bar_chart(market_cap_df: pd.DataFrame):
    """Build market cap bucket distribution bar chart."""
    if market_cap_df.empty:
        return None

    df = market_cap_df.copy()
    if (df["Weight"] > 1).any():
        df["Weight"] = df["Weight"] / 100.0

    fig = px.bar(
        df,
        x="Market Cap Bucket",
        y="Weight",
        color="Market Cap Bucket",
        color_discrete_sequence=_CHART_THEME["palette"],
        text_auto=".1%",
    )
    fig.update_yaxes(tickformat=".1%")
    fig.update_layout(showlegend=False)
    return _style_plotly_figure(fig, height=240)


def build_top_holdings_bar_chart(top_holdings: pd.DataFrame):
    """Build clean horizontal bar chart for top 10 holdings."""
    df = top_holdings.sort_values("Current Weight", ascending=True).tail(10).copy()
    weight_col = "Current Weight"
    if (df[weight_col] > 1).any():
        df["DisplayWeight"] = df[weight_col] / 100.0
    else:
        df["DisplayWeight"] = df[weight_col]

    fig = px.bar(
        df,
        x="DisplayWeight",
        y="Stock Name",
        orientation="h",
        color_discrete_sequence=[_CHART_THEME["primary"]],
        text_auto=".2%",
    )
    fig.update_xaxes(tickformat=".1%", title=None)
    fig.update_yaxes(title=None)
    return _style_plotly_figure(fig, height=290)


def build_research_returns_chart(return_chart_data: pd.DataFrame) -> go.Figure:
    """Build cross-fund return comparison grouped bars."""
    fig = px.bar(
        return_chart_data,
        x="Fund",
        y="Return",
        color="Metric",
        barmode="group",
        color_discrete_map={
            "Absolute Return": _CHART_THEME["primary"],
            "Benchmark Return": _CHART_THEME["benchmark"],
        },
        labels={"Return": "Return", "Fund": "Fund"},
    )
    fig.update_yaxes(tickformat=".1%")
    return _style_plotly_figure(fig, height=300)


def build_active_return_chart(active_chart_data: pd.DataFrame) -> go.Figure:
    """Build active return delta bar chart with positive/negative colors."""
    df = active_chart_data.copy()
    df["Color"] = df["Active Return"].apply(lambda v: _CHART_THEME["positive"] if v >= 0 else _CHART_THEME["negative"])

    fig = px.bar(
        df,
        x="Fund",
        y="Active Return",
        color="Color",
        color_discrete_map="identity",
        labels={"Active Return": "Active Return", "Fund": "Fund"},
    )
    fig.update_yaxes(tickformat="+.1%")
    fig.update_layout(showlegend=False)
    return _style_plotly_figure(fig, height=300)


def build_research_risk_chart(risk_chart_data: pd.DataFrame) -> go.Figure:
    """Build tracking error and drawdown comparison chart."""
    fig = px.bar(
        risk_chart_data,
        x="Fund",
        y="Risk",
        color="Metric",
        barmode="group",
        color_discrete_map={
            "Tracking Error": _CHART_THEME["primary"],
            "Max Drawdown": _CHART_THEME["negative"],
        },
        labels={"Risk": "Percentage", "Fund": "Fund"},
    )
    fig.update_yaxes(tickformat=".1%")
    return _style_plotly_figure(fig, height=300)


def build_monthly_contribution_chart(monthly_summary: pd.DataFrame) -> go.Figure:
    """Build monthly portfolio contribution Plotly chart with color coding."""
    df = monthly_summary.copy()
    df["Color"] = df["Total Contribution"].apply(lambda v: _CHART_THEME["positive"] if v >= 0 else _CHART_THEME["negative"])

    fig = px.bar(
        df,
        x="Month",
        y="Total Contribution",
        color="Color",
        color_discrete_map="identity",
        labels={"Total Contribution": "Contribution (pp)"},
    )
    fig.update_yaxes(tickformat="+.2f", title="Contribution (pp)")
    fig.update_layout(showlegend=False)
    return _style_plotly_figure(fig, height=280)


def build_sector_contribution_chart(sector_df: pd.DataFrame, month_label: str) -> go.Figure:
    """Build sector contribution bar chart for selected month."""
    df = sector_df.sort_values("Contribution", ascending=True).copy()
    df["Color"] = df["Contribution"].apply(lambda v: _CHART_THEME["positive"] if v >= 0 else _CHART_THEME["negative"])

    fig = px.bar(
        df,
        x="Contribution",
        y="Sector",
        orientation="h",
        color="Color",
        color_discrete_map="identity",
        labels={"Contribution": "Contribution (pp)"},
    )
    fig.update_xaxes(tickformat="+.2f", title="Contribution (pp)")
    fig.update_layout(showlegend=False)
    return _style_plotly_figure(fig, height=280)


def build_contributor_chart(df: pd.DataFrame, color: str = None) -> alt.Chart:
    """Build horizontal contributor Altair bar chart."""
    chart_color = color or _CHART_THEME["primary"]
    chart_df = df[["Stock Name", "Contribution"]].copy()

    return (
        alt.Chart(chart_df)
        .mark_bar(color=chart_color)
        .encode(
            x=alt.X(
                "Contribution:Q",
                title="Contribution (%)",
                axis=alt.Axis(
                    format=".2f",
                    gridColor=_CHART_THEME["grid"],
                    labelColor=_CHART_THEME["muted"],
                    labelFont="JetBrains Mono",
                ),
            ),
            y=alt.Y(
                "Stock Name:N",
                sort="-x",
                title=None,
                axis=alt.Axis(
                    labelColor=_CHART_THEME["text"],
                    labelFont="JetBrains Mono",
                ),
            ),
            tooltip=[
                "Stock Name",
                alt.Tooltip("Contribution:Q", format="+.2f", title="Contribution (%)"),
            ],
        )
        .properties(
            background="transparent",
            height=28 * max(len(chart_df), 1),
        )
    )
