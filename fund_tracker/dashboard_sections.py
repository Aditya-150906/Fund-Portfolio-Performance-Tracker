"""
dashboard_sections.py
---------------------
Streamlit rendering and pure display transformations for dashboard.py.

Domain calculations remain in performance.py, research.py, attribution.py,
and rebalance.py. This module only prepares display data, orchestrates those
existing functions, and renders the existing dashboard sections.
"""

from dataclasses import dataclass

import pandas as pd
import streamlit as st

import attribution
import dashboard_charts
import data_loader
import performance
import rebalance
import research


def build_research_display_frame(research_df: pd.DataFrame) -> pd.DataFrame:
    """Format the existing research result for dashboard display."""
    display_research = research_df.copy()
    percentage_columns = [
        "Absolute Return", "CAGR", "Benchmark Return", "Active Return",
        "Alpha", "Tracking Error", "Max Drawdown", "Volatility",
        "Benchmark Volatility", "Downside Deviation", "Jensen's Alpha",
    ]
    decimal_columns = [
        "Sharpe Ratio", "Sortino Ratio", "Beta", "Information Ratio",
    ]
    for column in percentage_columns:
        if column in display_research.columns:
            display_research[column] = display_research[column].apply(
                lambda value: f"{value:.2%}" if pd.notna(value) else "N/A"
            )
    for column in decimal_columns:
        if column in display_research.columns:
            display_research[column] = display_research[column].apply(
                lambda value: f"{value:.2f}" if pd.notna(value) else "N/A"
            )
    return display_research


def build_research_return_chart_frame(research_df: pd.DataFrame) -> pd.DataFrame:
    """Build the prepared return-comparison frame used by Plotly."""
    return research_df[
        ["Fund", "Absolute Return", "Benchmark Return"]
    ].copy().melt(
        id_vars="Fund",
        var_name="Metric",
        value_name="Return",
    )


def build_research_risk_chart_frame(research_df: pd.DataFrame) -> pd.DataFrame:
    """Build the prepared tracking-error/drawdown frame used by Plotly."""
    return research_df[
        ["Fund", "Tracking Error", "Max Drawdown"]
    ].copy().melt(
        id_vars="Fund",
        var_name="Metric",
        value_name="Risk",
    )


def build_fundamental_display_frame(
    detail_weightage: pd.DataFrame,
    mapping: pd.DataFrame,
    fundamental_data: pd.DataFrame,
) -> pd.DataFrame:
    """Merge and format the existing fundamental-research display table."""
    fundamental_holdings = detail_weightage.merge(
        mapping[["ISIN", "Yahoo Ticker"]],
        on="ISIN",
        how="left",
    )
    fundamental_holdings = fundamental_holdings.merge(
        fundamental_data,
        on=["ISIN", "Yahoo Ticker"],
        how="left",
    )
    if "Is Cash" in fundamental_holdings.columns:
        fundamental_holdings = fundamental_holdings[
            ~fundamental_holdings["Is Cash"]
        ].copy()

    fundamental_display = fundamental_holdings[
        [
            "Fund Name", "Stock Name", "ISIN", "Yahoo Ticker", "Current Weight",
            "Market Cap", "PE Ratio", "PB Ratio", "ROE", "Dividend Yield",
            "Debt to Equity",
        ]
    ].copy().rename(
        columns={
            "Fund Name": "Fund",
            "Stock Name": "Company",
            "Current Weight": "Weight",
            "PE Ratio": "P/E",
            "PB Ratio": "P/B",
            "Debt to Equity": "Debt / Equity",
        }
    )
    fundamental_display["Weight"] = fundamental_display["Weight"].map(
        lambda value: f"{value:.2f}%" if pd.notna(value) else "N/A"
    )
    fundamental_display["Market Cap"] = fundamental_display["Market Cap"].map(
        lambda value: f"{value / 1e12:.2f} T" if pd.notna(value) else "N/A"
    )
    fundamental_display["P/E"] = fundamental_display["P/E"].map(
        lambda value: f"{value:.2f}" if pd.notna(value) else "N/A"
    )
    fundamental_display["P/B"] = fundamental_display["P/B"].map(
        lambda value: f"{value:.2f}" if pd.notna(value) else "N/A"
    )
    fundamental_display["ROE"] = fundamental_display["ROE"].map(
        lambda value: f"{value:.2%}" if pd.notna(value) else "N/A"
    )
    fundamental_display["Dividend Yield"] = fundamental_display["Dividend Yield"].map(
        lambda value: f"{value:.2f}%" if pd.notna(value) else "N/A"
    )
    fundamental_display["Debt / Equity"] = fundamental_display["Debt / Equity"].map(
        lambda value: f"{value:.2f}" if pd.notna(value) else "N/A"
    )
    return fundamental_display


def build_monthly_attribution_summary(monthly_attribution: dict) -> pd.DataFrame:
    """Build the existing monthly attribution summary table."""
    return pd.DataFrame([
        {
            "Month": month,
            "Total Contribution": result["total_contribution"],
            "Window Start": result["window_start"],
            "Window End": result["window_end"],
        }
        for month, result in monthly_attribution.items()
    ])


def select_contributor_display_columns(contribution_df: pd.DataFrame) -> list:
    """Select contributor columns while retaining available Yahoo audit fields."""
    display_columns = [
        "Stock Name", "ISIN", "Current Weight", "Stock Return", "Contribution",
    ]
    if "Return Status" in contribution_df.columns:
        display_columns.append("Return Status")
    for audit_column in (
        "Return Start Date", "Return Start Close", "Return End Date", "Return End Close",
    ):
        if audit_column in contribution_df.columns:
            display_columns.append(audit_column)
    return display_columns


def build_holdings_change_display_frame(holdings_changes: pd.DataFrame) -> pd.DataFrame:
    """Return a display copy of the existing holdings-change result."""
    return holdings_changes.copy()


@dataclass(frozen=True)
class FundResearchState:
    """State needed by the later portfolio and fundamental sections."""

    detail_fund: str
    detail_period: str
    detail_result: dict | None
    detail_weightage: pd.DataFrame
    detail_fund_name: str


def render_performance_section(period_perf: dict) -> None:
    """Render the existing performance-by-period tabs."""
    period_tabs = st.tabs(performance.PERIOD_ORDER)
    for label, tab in zip(performance.PERIOD_ORDER, period_tabs):
        with tab:
            period_result = period_perf[label]
            if not period_result["Available"]:
                st.info(f"{label}: {period_result['Reason']}.")
                continue
            if period_result["Truncated"]:
                st.caption(
                    f"Fund history only goes back to "
                    f"{period_result['Window Start'].date()}."
                )
            pcol1, pcol2, pcol3, pcol4 = st.columns(4)
            pcol1.metric("Absolute Return", f"{period_result['Absolute Return']:.2%}")
            if period_result.get("CAGR Annualised", True):
                pcol2.metric("CAGR", f"{period_result['CAGR']:.2%}")
                pcol3.metric("Alpha", f"{period_result['Alpha']:.2%}")
            else:
                pcol2.metric(
                    "CAGR", "N/A",
                    help="Window is under 1 year - annualised CAGR would be misleading.",
                )
                pcol3.metric(
                    "Alpha", "N/A",
                    help="Alpha is not meaningful over a window under 1 year.",
                )
            pcol4.metric("Max Drawdown", f"{period_result['Maximum Drawdown']:.2%}")
            st.caption(
                f"Window: {period_result['Window Start'].date()} "
                f"to {period_result['Window End'].date()}"
            )
            period_daily = period_result["Daily"]
            if (
                period_daily.empty
                or (
                    period_daily[["Portfolio NAV", "Benchmark NAV"]] == 0
                ).all().all()
            ):
                st.warning("No valid Portfolio/Benchmark NAV data to chart for this window.")
            else:
                chart_col1, chart_col2 = st.columns(2)
                with chart_col1:
                    st.caption("NAV vs Benchmark (each on its own axis)")
                    st.altair_chart(
                        dashboard_charts.build_nav_vs_benchmark_chart(period_daily),
                        use_container_width=True,
                    )
                with chart_col2:
                    st.caption(
                        f"Growth (rebased to 0% at {period_result['Window Start'].date()})"
                    )
                    st.line_chart(dashboard_charts.build_growth_chart(period_daily))


def render_risk_section(perf: dict, fund_name: str, fund_code: str) -> None:
    """Render the existing risk metrics and rolling-risk charts."""
    summary = perf["summary"]
    st.markdown("---")
    st.subheader("Risk Analytics")
    st.caption(f"Risk metrics for {fund_name} ({fund_code}) over its full history.")
    rcol1, rcol2, rcol3, rcol4 = st.columns(4)
    rcol1.metric("Volatility", f"{summary.get('Volatility', float('nan')):.2%}")
    rcol2.metric("Sharpe Ratio", f"{summary.get('Sharpe Ratio', float('nan')):.2f}")
    rcol3.metric("Sortino Ratio", f"{summary.get('Sortino Ratio', float('nan')):.2f}")
    rcol4.metric("Downside Deviation", f"{summary.get('Downside Deviation', float('nan')):.2%}")
    rcol5, rcol6, rcol7, rcol8 = st.columns(4)
    rcol5.metric("Beta", f"{summary.get('Beta', float('nan')):.2f}")
    jensen_alpha = summary.get("Jensen's Alpha", float("nan"))
    rcol6.metric("Jensen's Alpha", f"{jensen_alpha:.2%}")
    rcol7.metric("Maximum Drawdown", f"{summary.get('Maximum Drawdown', float('nan')):.2%}")
    st.markdown("#### Risk Over Time")
    rchart1, rchart2, rchart3 = st.columns(3)
    with rchart1:
        st.caption("Rolling Volatility")
        st.altair_chart(
            dashboard_charts.build_rolling_metric_chart(
                perf["daily"], "Rolling Volatility", "#D35400"
            ),
            use_container_width=True,
        )
    with rchart2:
        st.caption("Rolling Sharpe Ratio")
        st.altair_chart(
            dashboard_charts.build_rolling_metric_chart(
                perf["daily"], "Rolling Sharpe", "#27AE60"
            ),
            use_container_width=True,
        )
    with rchart3:
        st.caption("Drawdown")
        st.altair_chart(
            dashboard_charts.build_drawdown_chart(perf["daily"]),
            use_container_width=True,
        )


def render_research_section(fund_data) -> pd.DataFrame:
    """Render fund comparison and research charts, returning raw results."""
    st.markdown("---")
    st.subheader("Fund Research Comparison")
    st.caption(
        "Compare configured funds using portfolio performance, "
        "benchmark-relative performance, active risk, and drawdown metrics."
    )
    research_period = st.selectbox(
        "Research period",
        performance.PERIOD_ORDER,
        key="research_period",
    )
    research_df = research.build_fund_comparison(fund_data, period=research_period)
    if research_df.empty:
        st.info(
            f"No funds have sufficient data available for the selected period: "
            f"{research_period}."
        )
        return research_df

    st.dataframe(
        build_research_display_frame(research_df),
        use_container_width=True,
        hide_index=True,
    )
    st.markdown("### Research Charts")
    st.plotly_chart(
        dashboard_charts.build_research_returns_chart(
            build_research_return_chart_frame(research_df)
        ),
        use_container_width=True,
    )
    active_chart_data = research_df[["Fund", "Active Return"]].copy()
    st.plotly_chart(
        dashboard_charts.build_active_return_chart(active_chart_data),
        use_container_width=True,
    )
    st.plotly_chart(
        dashboard_charts.build_research_risk_chart(
            build_research_risk_chart_frame(research_df)
        ),
        use_container_width=True,
    )
    return research_df


def render_fund_research_section(fund_data) -> FundResearchState:
    """Render selected-fund research detail and return downstream state."""
    st.markdown("---")
    st.subheader("Fund Research Detail")
    st.caption(
        "Inspect the selected fund's performance profile and latest portfolio composition."
    )
    detail_fund = st.selectbox(
        "Select fund for detailed research",
        sorted(fund_data.nav["Fund Code"].unique()),
        key="research_detail_fund",
    )
    detail_period = st.selectbox(
        "Detail period",
        performance.PERIOD_ORDER,
        key="research_detail_period",
    )
    detail_nav = (
        fund_data.nav[fund_data.nav["Fund Code"] == detail_fund]
        .sort_values("Date")
        .copy()
    )
    detail_result = performance.compute_multi_period_performance(detail_nav).get(detail_period)
    detail_weightage = fund_data.weightage[
        fund_data.weightage["Fund Code"] == detail_fund
    ]
    detail_fund_name = (
        detail_weightage["Fund Name"].iloc[0]
        if not detail_weightage.empty
        else detail_fund
    )
    if detail_result is None or not detail_result.get("Available", False):
        st.info(
            f"No performance data is available for {detail_fund_name} "
            f"for the selected period."
        )
        return FundResearchState(
            detail_fund, detail_period, detail_result, detail_weightage, detail_fund_name
        )

    latest_holdings = data_loader.latest_snapshot(fund_data.weightage, detail_fund)
    real_holdings = latest_holdings[~latest_holdings["Is Cash"]]
    st.markdown(f"### {detail_fund_name}")
    metric_1, metric_2, metric_3, metric_4 = st.columns(4)
    metric_1.metric(
        "Absolute Return",
        f"{detail_result['Absolute Return']:.2%}"
        if pd.notna(detail_result["Absolute Return"]) else "N/A",
    )
    metric_2.metric(
        "Benchmark Return",
        f"{detail_result['Benchmark Return']:.2%}"
        if pd.notna(detail_result["Benchmark Return"]) else "N/A",
    )
    metric_3.metric(
        "Active Return",
        f"{detail_result['Active Return']:.2%}"
        if pd.notna(detail_result["Active Return"]) else "N/A",
    )
    metric_4.metric(
        "Maximum Drawdown",
        f"{detail_result['Maximum Drawdown']:.2%}"
        if pd.notna(detail_result["Maximum Drawdown"]) else "N/A",
    )
    metric_5, metric_6, metric_7, metric_8 = st.columns(4)
    metric_5.metric(
        "CAGR",
        f"{detail_result['CAGR']:.2%}" if pd.notna(detail_result["CAGR"]) else "N/A",
    )
    metric_6.metric(
        "Tracking Error",
        f"{detail_result['Tracking Error']:.2%}"
        if pd.notna(detail_result["Tracking Error"]) else "N/A",
    )
    metric_7.metric(
        "Information Ratio",
        f"{detail_result['Information Ratio']:.2f}"
        if pd.notna(detail_result["Information Ratio"]) else "N/A",
    )
    metric_8.metric("Number of Holdings", f"{len(real_holdings):,}")
    latest_snapshot_date = latest_holdings["Date"].max()
    st.caption(
        f"Latest portfolio snapshot: {latest_snapshot_date.strftime('%b %Y')} | "
        f"Total reported weight: {latest_holdings['Current Weight'].sum():.2f}%"
    )
    return FundResearchState(
        detail_fund, detail_period, detail_result, detail_weightage, detail_fund_name
    )


def render_portfolio_analytics_section(
    fund_data,
    detail_fund: str,
    fundamental_data: pd.DataFrame,
    fund_codes: list,
) -> None:
    """Render the existing portfolio analytics section."""
    st.markdown("---")
    st.subheader("Portfolio Analytics")
    st.caption(
        "Portfolio concentration, sector mix, market-cap buckets, and overlap "
        "for the selected fund."
    )
    portfolio_analytics = research.build_portfolio_analytics(
        fund_data,
        detail_fund,
        fundamental_data=fundamental_data,
    )
    if not portfolio_analytics.get("Available", False):
        st.info(portfolio_analytics.get("Reason", "No portfolio analytics available."))
        return
    concentration = portfolio_analytics["Concentration"]
    pcol1, pcol2, pcol3, pcol4 = st.columns(4)
    pcol1.metric("Top 5 Holdings", f"{concentration['Top 5 Holdings Weight']:.2%}")
    pcol2.metric("Top 10 Holdings", f"{concentration['Top 10 Holdings Weight']:.2%}")
    pcol3.metric(
        "HHI",
        f"{concentration['HHI']:.4f}" if pd.notna(concentration["HHI"]) else "N/A",
    )
    pcol4.metric(
        "Effective Holdings",
        f"{concentration['Effective Number of Holdings']:.2f}"
        if pd.notna(concentration["Effective Number of Holdings"]) else "N/A",
    )
    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        st.caption("Top Holdings")
        top_holdings = portfolio_analytics["Top Holdings"][["Stock Name", "Current Weight"]].copy()
        top_holdings = top_holdings.sort_values("Current Weight", ascending=False).head(10)
        top_holdings["Current Weight"] = top_holdings["Current Weight"] / 100.0
        st.bar_chart(
            top_holdings.set_index("Stock Name")["Current Weight"],
            use_container_width=True,
        )
    with chart_col2:
        st.caption("Sector Allocation")
        sector_chart = portfolio_analytics["Sector Allocation"].copy()
        if not sector_chart.empty:
            st.bar_chart(sector_chart.set_index("Sector")["Weight"], use_container_width=True)
        else:
            st.caption("No sector allocation available.")
    if not portfolio_analytics["Market Cap Allocation"].empty:
        st.caption("Market-Cap Allocation")
        st.bar_chart(
            portfolio_analytics["Market Cap Allocation"].set_index("Market Cap Bucket")["Weight"],
            use_container_width=True,
        )
    if len(fund_codes) > 1:
        st.caption("Holdings Overlap vs Other Funds")
        overlap_table = research.compare_funds_for_overlap(
            fund_data,
            [detail_fund] + [fund for fund in fund_codes if fund != detail_fund],
        )
        if not overlap_table.empty:
            overlap_table["Holding Overlap Ratio"] = overlap_table["Holding Overlap Ratio"].map(
                lambda value: f"{value:.2%}" if pd.notna(value) else "N/A"
            )
            overlap_table["Weight Overlap"] = overlap_table["Weight Overlap"].map(
                lambda value: f"{value:.2%}" if pd.notna(value) else "N/A"
            )
            st.dataframe(overlap_table, use_container_width=True, hide_index=True)


def render_fundamental_section(
    detail_weightage: pd.DataFrame,
    mapping: pd.DataFrame,
    fundamental_data: pd.DataFrame,
) -> None:
    """Render the existing fundamental-research table."""
    st.markdown("---")
    st.subheader("Fundamental Research")
    st.caption(
        "Fundamental metrics for the companies currently held by the selected research fund."
    )
    st.dataframe(
        build_fundamental_display_frame(detail_weightage, mapping, fundamental_data),
        use_container_width=True,
        hide_index=True,
    )


def render_holdings_changes_section(
    holdings: pd.DataFrame,
    previous_holdings: pd.DataFrame,
    threshold: float,
) -> pd.DataFrame:
    """Render portfolio weightage/rebalance output and return drift results."""
    st.markdown("### Portfolio Weightage")
    st.caption(
        "Current holding weights for this snapshot. Rows highlighted in red have moved by more "
        "than the drift threshold versus the previous month-end snapshot."
    )
    rebalance_df = rebalance.compute_weight_drift(
        holdings,
        previous_holdings,
        threshold=threshold,
    )
    if previous_holdings is None:
        st.info(
            "This is the earliest available snapshot for this fund - every holding is shown as "
            "new because there is no prior month to compare drift against."
        )
    rebalance_display = rebalance_df.copy()
    rebalance_display.index = range(1, len(rebalance_display) + 1)
    st.dataframe(
        rebalance_display.style.apply(
            lambda row: [
                "background-color: #FCE4E4" if row["Rebalance Required"] else ""
                for _ in row
            ],
            axis=1,
        ).format(
            {
                "Current Weight": "{:.2f}%",
                "Previous Weight": "{:.2f}%",
                "Drift": "{:+.2f}pp",
            }
        ),
        use_container_width=True,
    )
    return rebalance_df


@st.cache_data(
    show_spinner="Fetching historical monthly attribution from Yahoo Finance..."
)
def _load_historical_attribution(_weightage, _mapping, _sector_data, selected_fund_code):
    fund_weightage = _weightage[
        _weightage["Fund Code"] == selected_fund_code
    ].copy()
    if _sector_data is not None and not _sector_data.empty:
        sector_columns = [
            column for column in ["ISIN", "Sector"] if column in _sector_data.columns
        ]
        if len(sector_columns) == 2:
            fund_weightage = fund_weightage.merge(
                _sector_data[sector_columns].drop_duplicates("ISIN"),
                on="ISIN",
                how="left",
            )
    return attribution.compute_monthly_attribution(
        fund_weightage,
        _mapping,
        top_n=5,
    )


def render_historical_attribution_section(
    weightage: pd.DataFrame,
    mapping: pd.DataFrame,
    sector_data: pd.DataFrame,
    fund_code: str,
    holdings: pd.DataFrame,
    previous_holdings: pd.DataFrame,
) -> None:
    """Render historical attribution and latest holdings-change output."""
    st.markdown("---")
    st.subheader("Historical Attribution & Holdings Changes")
    st.caption(
        "Each month uses that month's portfolio snapshot and its own stock-return window. "
        "Contribution is shown in percentage points."
    )
    if st.button("Load historical attribution", key="load_historical_attribution"):
        historical_attribution = _load_historical_attribution(
            weightage, mapping, sector_data, fund_code
        )
        st.session_state["historical_attribution_result"] = (
            fund_code,
            historical_attribution,
        )
    historical_result = st.session_state.get("historical_attribution_result")
    if historical_result is not None and historical_result[0] == fund_code:
        historical_attribution = historical_result[1]
        if not historical_attribution:
            st.info("At least two snapshots are required for historical attribution.")
        else:
            monthly_summary = build_monthly_attribution_summary(historical_attribution)
            st.plotly_chart(
                dashboard_charts.build_monthly_contribution_chart(monthly_summary),
                use_container_width=True,
            )
            st.dataframe(
                monthly_summary.style.format(
                    {"Total Contribution": "{:+.2f}pp"}, na_rep="-"
                ),
                use_container_width=True,
                hide_index=True,
            )
            historical_months = list(historical_attribution.keys())
            selected_month = st.selectbox(
                "Attribution month",
                historical_months,
                format_func=lambda month: pd.Timestamp(month).strftime("%b %Y"),
                key="historical_attribution_month",
            )
            selected_result = historical_attribution[selected_month]
            top_month, bottom_month = attribution.top_bottom_contributors(
                selected_result["data"], n=5
            )
            display_columns = select_contributor_display_columns(selected_result["data"])
            top_col, bottom_col = st.columns(2)
            for column, title, frame in (
                (top_col, "Top Contributors", top_month),
                (bottom_col, "Bottom Contributors", bottom_month),
            ):
                with column:
                    st.markdown(f"**{title}**")
                    st.dataframe(
                        frame[display_columns].style.format(
                            {
                                "Current Weight": "{:.2f}%",
                                "Stock Return": "{:+.2%}",
                                "Contribution": "{:+.2f}pp",
                            },
                            na_rep="-",
                        ),
                        use_container_width=True,
                        hide_index=True,
                    )
            selected_sector = selected_result["sector"].copy()
            if not selected_sector.empty:
                st.markdown("**Sector Attribution**")
                st.plotly_chart(
                    dashboard_charts.build_sector_contribution_chart(
                        selected_sector,
                        pd.Timestamp(selected_month).strftime("%b %Y"),
                    ),
                    use_container_width=True,
                )
                st.dataframe(
                    selected_sector.style.format(
                        {"Contribution": "{:+.2f}pp", "Weight": "{:.2f}%"},
                        na_rep="-",
                    ),
                    use_container_width=True,
                    hide_index=True,
                )

    st.markdown("**Latest Holdings Changes**")
    holdings_changes = rebalance.compute_holdings_changes(holdings, previous_holdings)
    st.dataframe(
        build_holdings_change_display_frame(holdings_changes).style.format(
            {
                "Previous Weight": "{:.2f}%",
                "Current Weight": "{:.2f}%",
                "Weight Change": "{:+.2f}pp",
            },
            na_rep="-",
        ),
        use_container_width=True,
        hide_index=True,
    )


@st.cache_data(
    show_spinner="Fetching this month's stock price history from Yahoo Finance..."
)
def _load_month_contributions(_fund_weightage, _mapping, fund_code, month_end_ts):
    fund_only = _fund_weightage[_fund_weightage["Fund Code"] == fund_code]
    previous_snap = data_loader.previous_snapshot(
        fund_only,
        fund_code,
        before_date=month_end_ts,
    )
    previous_month_end = (
        previous_snap["Date"].iloc[0] if previous_snap is not None else None
    )
    contrib_df = attribution.compute_stock_contributions_for_month(
        fund_only,
        _mapping,
        month_end=month_end_ts,
        previous_month_end=previous_month_end,
    )
    return contrib_df, previous_month_end


def render_attribution_section(
    weightage: pd.DataFrame,
    mapping: pd.DataFrame,
    fund_code: str,
    available_dates: list,
) -> None:
    """Render the existing monthly best/worst contributor section."""
    st.markdown("---")
    st.markdown("### Monthly Best & Worst Contributors")
    st.caption(
        "Pick a month-end snapshot to calculate the stock-level contribution for that month."
    )
    contributor_dates = [date for date in available_dates if date != min(available_dates)]
    if not contributor_dates:
        st.info("This fund only has one month-end snapshot so far - nothing to compare yet.")
        return
    contrib_month = st.selectbox(
        "Month",
        contributor_dates,
        format_func=lambda date: date.strftime("%b %Y"),
        key="contrib_month_select",
    )
    contrib_month_ts = pd.Timestamp(contrib_month)
    if st.button("Fetch contributors for this month"):
        month_df, previous_month_end = _load_month_contributions(
            weightage,
            mapping,
            fund_code,
            contrib_month_ts,
        )
        st.session_state["monthly_contrib_result"] = (
            contrib_month_ts,
            month_df,
            previous_month_end,
        )
    result = st.session_state.get("monthly_contrib_result")
    if result is None or result[0] != contrib_month_ts:
        if result is not None:
            st.caption(
                "Selected month has changed - click **Fetch contributors for this month** to load it."
            )
        return
    _, month_df, previous_month_end = result
    if month_df.empty:
        st.info("No monthly return could be computed for this snapshot.")
        return
    st.caption(
        f"Stock returns calculated from **{previous_month_end.date()}** to "
        f"**{contrib_month_ts.date()}**."
    )
    failure_reason = attribution.all_fetches_failed(month_df)
    if failure_reason:
        st.error(
            f"Every holding's return fetch failed for this month "
            f"(reason: {failure_reason})."
        )
    elif (
        "Return Status" in month_df.columns
        and month_df["Return Status"].astype(str).str.startswith("Fetch Failed").any()
    ):
        n_failed = month_df["Return Status"].astype(str).str.startswith("Fetch Failed").sum()
        st.warning(
            f"{n_failed} of {len(month_df)} holding(s) show 0.00% because their return fetch failed."
        )
    if (
        "Return Status" in month_df.columns
        and month_df["Return Status"].astype(str).str.contains("Verify", na=False).any()
    ):
        flagged = month_df[
            month_df["Return Status"].astype(str).str.contains("Verify", na=False)
        ]
        st.warning(
            f"{len(flagged)} holding(s) have a Stock Return that should be manually verified."
        )
    top5, bottom5 = attribution.top_bottom_contributors(month_df, n=5)
    display_columns = select_contributor_display_columns(month_df)
    col_best, col_worst = st.columns(2)
    with col_best:
        st.markdown(f"**Top 5 - {contrib_month_ts.strftime('%b %Y')}**")
        st.altair_chart(
            dashboard_charts.build_contributor_chart(top5, "#1F4E78"),
            use_container_width=True,
        )
        st.dataframe(
            top5[display_columns].style.format(
                {
                    "Current Weight": "{:.2f}%",
                    "Stock Return": "{:+.2%}",
                    "Contribution": "{:+.2f}%",
                },
                na_rep="-",
            ),
            use_container_width=True,
            hide_index=True,
        )
    with col_worst:
        st.markdown(f"**Bottom 5 - {contrib_month_ts.strftime('%b %Y')}**")
        st.altair_chart(
            dashboard_charts.build_contributor_chart(bottom5, "#C0392B"),
            use_container_width=True,
        )
        st.dataframe(
            bottom5[display_columns].style.format(
                {
                    "Current Weight": "{:.2f}%",
                    "Stock Return": "{:+.2%}",
                    "Contribution": "{:+.2f}%",
                },
                na_rep="-",
            ),
            use_container_width=True,
            hide_index=True,
        )