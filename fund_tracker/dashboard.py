"""
dashboard.py
------------
The primary, hosted front-end over the same pipeline used by main.py.
"""

import pandas as pd
import streamlit as st

import attribution
import config
import data_loader
import dashboard_charts
import dashboard_sidebar
import performance
import research
import rebalance
import report_generator
import yahoo_fetch


st.set_page_config(
    page_title="Fund/Portfolio Performance Tracker",
    layout="wide",
)

st.title("Fund / Portfolio Performance Tracker")


dashboard_sidebar.render_file_management_sidebar()


# =============================================================================
# CACHED DATA LOADERS
# =============================================================================

@st.cache_data(
    show_spinner="Loading and validating inputs..."
)
def _load_data():

    return data_loader.load_all()


@st.cache_data(
    show_spinner="Fetching sector data from Yahoo Finance..."
)
def _load_sectors(_mapping):

    return yahoo_fetch.fetch_sector_data(
        _mapping
    )


@st.cache_data(
    show_spinner="Fetching fundamental data from Yahoo Finance..."
)
def _load_fundamentals(_mapping):

    return yahoo_fetch.fetch_fundamental_data(
        _mapping
    )


# =============================================================================
# CHECK REQUIRED FILES
# =============================================================================

if not (
    config.has_weightage_files()
    and config.has_nav_files()
    and config.has_nse_security_master()
    and config.has_bse_security_master()
):

    st.info(
        "**Get started:** upload both Security Master files and at least "
        "one fund's Weightage + Daily NAV files using the sidebar."
    )

    st.stop()


# =============================================================================
# LOAD FUND DATA
# =============================================================================

try:

    fund_data = _load_data()

except (
    FileNotFoundError,
    ValueError,
) as exc:

    st.error(
        str(exc)
    )

    st.stop()


sector_data = _load_sectors(
    fund_data.mapping
)

fundamental_data = _load_fundamentals(
    fund_data.mapping
)


fund_codes = data_loader.get_fund_codes(
    fund_data
)


# =============================================================================
# FUND SELECTION
# =============================================================================

sidebar_state = dashboard_sidebar.render_sidebar_selection(fund_data)
fund_code = sidebar_state.fund_code
snapshot_date = sidebar_state.snapshot_date
threshold = sidebar_state.threshold
available_dates = sidebar_state.available_dates


# =============================================================================
# CURRENT FUND DATA
# =============================================================================

fund_weightage = data_loader.latest_snapshot(
    fund_data.weightage,
    fund_code,
    as_of=str(snapshot_date),
)


fund_nav = fund_data.nav[
    fund_data.nav["Fund Code"]
    == fund_code
].copy()


fund_name = fund_weightage[
    "Fund Name"
].iloc[0]


st.subheader(
    f"{fund_name} ({fund_code}) - "
    f"{snapshot_date.strftime('%b %Y')} snapshot"
)


holdings = fund_weightage.merge(
    fund_data.mapping[
        [
            "ISIN",
            "Yahoo Ticker",
        ]
    ],
    on="ISIN",
    how="left",
)


holdings = yahoo_fetch.merge_sector_with_holdings(
    holdings,
    sector_data,
)


# =============================================================================
# PERFORMANCE
# =============================================================================

perf = performance.compute_fund_performance(
    fund_nav
)

s = perf["summary"]


period_perf = (
    performance.compute_multi_period_performance(
        fund_nav
    )
)


period_tabs = st.tabs(
    performance.PERIOD_ORDER
)


for label, tab in zip(
    performance.PERIOD_ORDER,
    period_tabs,
):

    with tab:

        ps = period_perf[label]


        if not ps["Available"]:

            st.info(
                f"{label}: {ps['Reason']}."
            )

            continue


        if ps["Truncated"]:

            st.caption(
                f"Fund history only goes back to "
                f"{ps['Window Start'].date()} for this snapshot."
            )


        pcol1, pcol2, pcol3, pcol4 = st.columns(
            4
        )


        pcol1.metric(
            "Absolute Return",
            f"{ps['Absolute Return']:.2%}",
        )


        if ps.get(
            "CAGR Annualised",
            True,
        ):

            pcol2.metric(
                "CAGR",
                f"{ps['CAGR']:.2%}",
            )

        else:

            pcol2.metric(
                "CAGR",
                "N/A",
                help=(
                    "Window is under 1 year - "
                    "annualised CAGR would be misleading."
                ),
            )


        if ps.get(
            "CAGR Annualised",
            True,
        ):

            pcol3.metric(
                "Alpha",
                f"{ps['Alpha']:.2%}",
            )

        else:

            pcol3.metric(
                "Alpha",
                "N/A",
                help=(
                    "Alpha is not meaningful over "
                    "a window under 1 year."
                ),
            )


        pcol4.metric(
            "Max Drawdown",
            f"{ps['Maximum Drawdown']:.2%}",
        )


        st.caption(
            f"Window: "
            f"{ps['Window Start'].date()} "
            f"to "
            f"{ps['Window End'].date()}"
        )


        period_daily = ps["Daily"]


        if (
            period_daily.empty
            or (
                period_daily[
                    [
                        "Portfolio NAV",
                        "Benchmark NAV",
                    ]
                ]
                == 0
            ).all().all()
        ):

            st.warning(
                "No valid Portfolio/Benchmark NAV data "
                "to chart for this window."
            )

        else:

            chart_col1, chart_col2 = st.columns(
                2
            )


            with chart_col1:

                st.caption(
                    "NAV vs Benchmark "
                    "(each on its own axis)"
                )

                st.altair_chart(
                    dashboard_charts.build_nav_vs_benchmark_chart(
                        period_daily
                    ),
                    use_container_width=True,
                )


            with chart_col2:

                st.caption(
                    "Growth "
                    f"(rebased to 0% at "
                    f"{ps['Window Start'].date()})"
                )

                st.line_chart(
                    dashboard_charts.build_growth_chart(
                        period_daily
                    )
                )



# =============================================================================
# RISK ANALYTICS
# =============================================================================

st.markdown("---")
st.subheader("Risk Analytics")
st.caption(f"Risk metrics for {fund_name} ({fund_code}) over its full history.")

rcol1, rcol2, rcol3, rcol4 = st.columns(4)
rcol1.metric("Volatility", f"{s.get('Volatility', float('nan')):.2%}")
rcol2.metric("Sharpe Ratio", f"{s.get('Sharpe Ratio', float('nan')):.2f}")
rcol3.metric("Sortino Ratio", f"{s.get('Sortino Ratio', float('nan')):.2f}")
rcol4.metric("Downside Deviation", f"{s.get('Downside Deviation', float('nan')):.2%}")

rcol5, rcol6, rcol7, rcol8 = st.columns(4)
rcol5.metric("Beta", f"{s.get('Beta', float('nan')):.2f}")
jensen_alpha = s.get("Jensen's Alpha", float("nan"))
rcol6.metric("Jensen's Alpha", f"{jensen_alpha:.2%}")
rcol7.metric("Maximum Drawdown", f"{s.get('Maximum Drawdown', float('nan')):.2%}")

st.markdown("#### Risk Over Time")

rchart1, rchart2, rchart3 = st.columns(3)

with rchart1:
    st.caption("Rolling Volatility")
    st.altair_chart(dashboard_charts.build_rolling_metric_chart(perf["daily"], "Rolling Volatility", "#D35400"), use_container_width=True)

with rchart2:
    st.caption("Rolling Sharpe Ratio")
    st.altair_chart(dashboard_charts.build_rolling_metric_chart(perf["daily"], "Rolling Sharpe", "#27AE60"), use_container_width=True)

with rchart3:
    st.caption("Drawdown")
    st.altair_chart(dashboard_charts.build_drawdown_chart(perf["daily"]), use_container_width=True)


# =============================================================================
# FUND RESEARCH COMPARISON
# =============================================================================

st.markdown("---")

st.subheader(
    "Fund Research Comparison"
)


st.caption(
    "Compare configured funds using portfolio "
    "performance, benchmark-relative performance, "
    "active risk, and drawdown metrics."
)


research_period = st.selectbox(
    "Research period",
    performance.PERIOD_ORDER,
    key="research_period",
)


research_df = research.build_fund_comparison(
    fund_data,
    period=research_period,
)


if research_df.empty:

    st.info(
        f"No funds have sufficient data available "
        f"for the selected period: "
        f"{research_period}."
    )

else:

    display_research = research_df.copy()


    percentage_columns = [
        "Absolute Return",
        "CAGR",
        "Benchmark Return",
        "Active Return",
        "Alpha",
        "Tracking Error",
        "Max Drawdown",
        "Volatility",
        "Benchmark Volatility",
        "Downside Deviation",
        "Jensen's Alpha",
    ]

    decimal_columns = [
        "Sharpe Ratio",
        "Sortino Ratio",
        "Beta",
        "Information Ratio",
    ]

    for column in percentage_columns:
        if column in display_research.columns:
            display_research[column] = (
                display_research[column].apply(
                    lambda x: f"{x:.2%}" if pd.notna(x) else "N/A"
                )
            )

    for column in decimal_columns:
        if column in display_research.columns:
            display_research[column] = (
                display_research[column].apply(
                    lambda x: f"{x:.2f}" if pd.notna(x) else "N/A"
                )
            )

    display_research[
        "Information Ratio"
    ] = display_research[
        "Information Ratio"
    ].apply(
        lambda x:
            f"{x:.2f}"
            if pd.notna(x)
            else "N/A"
    )


    st.dataframe(
        display_research,
        use_container_width=True,
        hide_index=True,
    )


    # -------------------------------------------------------------------------
    # RESEARCH CHARTS
    # -------------------------------------------------------------------------

    st.markdown(
        "### Research Charts"
    )


    chart_data = research_df.copy()


    # Portfolio Return vs Benchmark

    return_chart_data = chart_data[
        [
            "Fund",
            "Absolute Return",
            "Benchmark Return",
        ]
    ].copy()


    return_chart_data = return_chart_data.melt(
        id_vars="Fund",
        var_name="Metric",
        value_name="Return",
    )


    fig_returns = dashboard_charts.build_research_returns_chart(
        return_chart_data
    )


    st.plotly_chart(
        fig_returns,
        use_container_width=True,
    )


    # Active Return

    active_chart_data = chart_data[
        [
            "Fund",
            "Active Return",
        ]
    ].copy()


    fig_active = dashboard_charts.build_active_return_chart(
        active_chart_data
    )


    st.plotly_chart(
        fig_active,
        use_container_width=True,
    )


    # Risk and Drawdown

    risk_chart_data = chart_data[
        [
            "Fund",
            "Tracking Error",
            "Max Drawdown",
        ]
    ].copy()


    risk_chart_data = risk_chart_data.melt(
        id_vars="Fund",
        var_name="Metric",
        value_name="Risk",
    )


    fig_risk = dashboard_charts.build_research_risk_chart(
        risk_chart_data
    )


    st.plotly_chart(
        fig_risk,
        use_container_width=True,
    )


# =============================================================================
# FUND RESEARCH DETAIL
# =============================================================================

st.markdown("---")

st.subheader(
    "Fund Research Detail"
)


st.caption(
    "Inspect the selected fund's performance "
    "profile and latest portfolio composition."
)


detail_fund = st.selectbox(
    "Select fund for detailed research",
    sorted(
        fund_data.nav[
            "Fund Code"
        ].unique()
    ),
    key="research_detail_fund",
)


detail_period = st.selectbox(
    "Detail period",
    performance.PERIOD_ORDER,
    key="research_detail_period",
)


detail_nav = (
    fund_data.nav[
        fund_data.nav["Fund Code"]
        == detail_fund
    ]
    .sort_values("Date")
    .copy()
)


detail_results = (
    performance.compute_multi_period_performance(
        detail_nav
    )
)


detail_result = detail_results.get(
    detail_period
)


detail_weightage = fund_data.weightage[
    fund_data.weightage["Fund Code"]
    == detail_fund
]


if detail_weightage.empty:

    detail_fund_name = detail_fund

else:

    detail_fund_name = (
        detail_weightage[
            "Fund Name"
        ].iloc[0]
    )


if (
    detail_result is None
    or not detail_result.get(
        "Available",
        False,
    )
):

    st.info(
        f"No performance data is available "
        f"for {detail_fund_name} "
        f"for the selected period."
    )


else:

    latest_holdings = (
        data_loader.latest_snapshot(
            fund_data.weightage,
            detail_fund,
        )
    )


    real_holdings = latest_holdings[
        ~latest_holdings["Is Cash"]
    ]


    number_of_holdings = len(
        real_holdings
    )


    total_weight = (
        latest_holdings[
            "Current Weight"
        ].sum()
    )


    st.markdown(
        f"### {detail_fund_name}"
    )


    metric_1, metric_2, metric_3, metric_4 = (
        st.columns(4)
    )


    metric_1.metric(
        "Absolute Return",
        (
            f"{detail_result['Absolute Return']:.2%}"
            if pd.notna(
                detail_result[
                    "Absolute Return"
                ]
            )
            else "N/A"
        ),
    )


    metric_2.metric(
        "Benchmark Return",
        (
            f"{detail_result['Benchmark Return']:.2%}"
            if pd.notna(
                detail_result[
                    "Benchmark Return"
                ]
            )
            else "N/A"
        ),
    )


    metric_3.metric(
        "Active Return",
        (
            f"{detail_result['Active Return']:.2%}"
            if pd.notna(
                detail_result[
                    "Active Return"
                ]
            )
            else "N/A"
        ),
    )


    metric_4.metric(
        "Maximum Drawdown",
        (
            f"{detail_result['Maximum Drawdown']:.2%}"
            if pd.notna(
                detail_result[
                    "Maximum Drawdown"
                ]
            )
            else "N/A"
        ),
    )


    metric_5, metric_6, metric_7, metric_8 = (
        st.columns(4)
    )


    metric_5.metric(
        "CAGR",
        (
            f"{detail_result['CAGR']:.2%}"
            if pd.notna(
                detail_result["CAGR"]
            )
            else "N/A"
        ),
    )


    metric_6.metric(
        "Tracking Error",
        (
            f"{detail_result['Tracking Error']:.2%}"
            if pd.notna(
                detail_result[
                    "Tracking Error"
                ]
            )
            else "N/A"
        ),
    )


    metric_7.metric(
        "Information Ratio",
        (
            f"{detail_result['Information Ratio']:.2f}"
            if pd.notna(
                detail_result[
                    "Information Ratio"
                ]
            )
            else "N/A"
        ),
    )


    metric_8.metric(
        "Number of Holdings",
        f"{number_of_holdings:,}",
    )


    latest_snapshot_date = (
        latest_holdings["Date"].max()
    )


    st.caption(
        f"Latest portfolio snapshot: "
        f"{latest_snapshot_date.strftime('%b %Y')} | "
        f"Total reported weight: "
        f"{total_weight:.2f}%"
    )


# =============================================================================
# PORTFOLIO ANALYTICS
# =============================================================================

st.markdown("---")
st.subheader("Portfolio Analytics")
st.caption("Portfolio concentration, sector mix, market-cap buckets, and overlap for the selected fund.")

portfolio_analytics = research.build_portfolio_analytics(
    fund_data,
    detail_fund,
    fundamental_data=fundamental_data,
)

if not portfolio_analytics.get("Available", False):
    st.info(portfolio_analytics.get("Reason", "No portfolio analytics available."))
else:
    top_5 = portfolio_analytics["Concentration"]["Top 5 Holdings Weight"]
    top_10 = portfolio_analytics["Concentration"]["Top 10 Holdings Weight"]
    hhi_val = portfolio_analytics["Concentration"]["HHI"]
    eff_holdings = portfolio_analytics["Concentration"]["Effective Number of Holdings"]

    pcol1, pcol2, pcol3, pcol4 = st.columns(4)
    pcol1.metric("Top 5 Holdings", f"{top_5:.2%}")
    pcol2.metric("Top 10 Holdings", f"{top_10:.2%}")
    pcol3.metric("HHI", f"{hhi_val:.4f}" if pd.notna(hhi_val) else "N/A")
    pcol4.metric("Effective Holdings", f"{eff_holdings:.2f}" if pd.notna(eff_holdings) else "N/A")

    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        st.caption("Top Holdings")
        top_holdings = portfolio_analytics["Top Holdings"][ ["Stock Name", "Current Weight"] ].copy()
        top_holdings = top_holdings.sort_values("Current Weight", ascending=False).head(10)
        top_holdings["Current Weight"] = top_holdings["Current Weight"] / 100.0
        st.bar_chart(top_holdings.set_index("Stock Name")["Current Weight"], use_container_width=True)

    with chart_col2:
        st.caption("Sector Allocation")
        sector_chart = portfolio_analytics["Sector Allocation"].copy()
        if not sector_chart.empty:
            sector_chart["Weight"] = sector_chart["Weight"]
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
        overlap_table = research.compare_funds_for_overlap(fund_data, [detail_fund] + [f for f in fund_codes if f != detail_fund])
        if not overlap_table.empty:
            overlap_table["Holding Overlap Ratio"] = overlap_table["Holding Overlap Ratio"].map(lambda x: f"{x:.2%}" if pd.notna(x) else "N/A")
            overlap_table["Weight Overlap"] = overlap_table["Weight Overlap"].map(lambda x: f"{x:.2%}" if pd.notna(x) else "N/A")
            st.dataframe(overlap_table, use_container_width=True, hide_index=True)


# =============================================================================
# FUNDAMENTAL RESEARCH
# =============================================================================

st.markdown("---")

st.subheader(
    "Fundamental Research"
)


st.caption(
    "Fundamental metrics for the companies currently "
    "held by the selected research fund."
)


# Start from the selected fund's weightage data.
# The raw Weightage data contains ISIN but not Yahoo Ticker,
# so first merge the ticker mapping.
fundamental_holdings = detail_weightage.merge(
    fund_data.mapping[
        [
            "ISIN",
            "Yahoo Ticker",
        ]
    ],
    on="ISIN",
    how="left",
)


# Add Yahoo Finance fundamental metrics.
fundamental_holdings = fundamental_holdings.merge(
    fundamental_data,
    on=[
        "ISIN",
        "Yahoo Ticker",
    ],
    how="left",
)


# Cash is not a company and therefore should not appear
# in the fundamental research table.
if "Is Cash" in fundamental_holdings.columns:

    fundamental_holdings = fundamental_holdings[
        ~fundamental_holdings["Is Cash"]
    ].copy()


fundamental_display = fundamental_holdings[
    [
        "Fund Name",
        "Stock Name",
        "ISIN",
        "Yahoo Ticker",
        "Current Weight",
        "Market Cap",
        "PE Ratio",
        "PB Ratio",
        "ROE",
        "Dividend Yield",
        "Debt to Equity",
    ]
].copy()


fundamental_display = fundamental_display.rename(
    columns={
        "Fund Name": "Fund",
        "Stock Name": "Company",
        "Current Weight": "Weight",
        "PE Ratio": "P/E",
        "PB Ratio": "P/B",
        "Debt to Equity": "Debt / Equity",
    }
)


# -------------------------------------------------------------------------
# Formatting
# -------------------------------------------------------------------------

fundamental_display["Weight"] = (
    fundamental_display["Weight"].map(
        lambda x:
            f"{x:.2f}%"
            if pd.notna(x)
            else "N/A"
    )
)


fundamental_display["Market Cap"] = (
    fundamental_display["Market Cap"].map(
        lambda x:
            f"{x / 1e12:.2f} T"
            if pd.notna(x)
            else "N/A"
    )
)


fundamental_display["P/E"] = (
    fundamental_display["P/E"].map(
        lambda x:
            f"{x:.2f}"
            if pd.notna(x)
            else "N/A"
    )
)


fundamental_display["P/B"] = (
    fundamental_display["P/B"].map(
        lambda x:
            f"{x:.2f}"
            if pd.notna(x)
            else "N/A"
    )
)


fundamental_display["ROE"] = (
    fundamental_display["ROE"].map(
        lambda x:
            f"{x:.2%}"
            if pd.notna(x)
            else "N/A"
    )
)


fundamental_display["Dividend Yield"] = (
    fundamental_display[
        "Dividend Yield"
    ].map(
        lambda x:
            f"{x:.2f}%"
            if pd.notna(x)
            else "N/A"
    )
)


fundamental_display["Debt / Equity"] = (
    fundamental_display[
        "Debt / Equity"
    ].map(
        lambda x:
            f"{x:.2f}"
            if pd.notna(x)
            else "N/A"
    )
)


st.dataframe(
    fundamental_display,
    use_container_width=True,
    hide_index=True,
)


# =============================================================================
# PORTFOLIO WEIGHTAGE
# =============================================================================

st.markdown(
    "### Portfolio Weightage"
)


st.caption(
    "Current holding weights for this snapshot. "
    "Rows highlighted in red have moved by more than "
    "the drift threshold versus the previous month-end snapshot."
)


previous_holdings = (
    data_loader.previous_snapshot(
        fund_data.weightage,
        fund_code,
        before_date=snapshot_date,
    )
)


rebalance_df = (
    rebalance.compute_weight_drift(
        holdings,
        previous_holdings,
        threshold=threshold,
    )
)


if previous_holdings is None:

    st.info(
        "This is the earliest available snapshot "
        "for this fund - every holding is shown as "
        "new because there is no prior month to "
        "compare drift against."
    )


rebalance_display = (
    rebalance_df.copy()
)


rebalance_display.index = range(
    1,
    len(rebalance_display) + 1,
)


st.dataframe(
    rebalance_display.style.apply(
        lambda r: [
            (
                "background-color: #FCE4E4"
                if r["Rebalance Required"]
                else ""
            )
            for _ in r
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


# =============================================================================
# PHASE 4: HISTORICAL ATTRIBUTION & HOLDINGS CHANGES
# =============================================================================

st.markdown("---")
st.subheader("Historical Attribution & Holdings Changes")
st.caption(
    "Each month uses that month's portfolio snapshot and its own stock-return window. "
    "Contribution is shown in percentage points."
)


@st.cache_data(
    show_spinner="Fetching historical monthly attribution from Yahoo Finance..."
)
def _load_historical_attribution(_weightage, _mapping, _sector_data, selected_fund_code):
    fund_weightage = _weightage[
        _weightage["Fund Code"] == selected_fund_code
    ].copy()
    if _sector_data is not None and not _sector_data.empty:
        sector_columns = [column for column in ["ISIN", "Sector"] if column in _sector_data.columns]
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


if st.button("Load historical attribution", key="load_historical_attribution"):
    historical_attribution = _load_historical_attribution(
        fund_data.weightage,
        fund_data.mapping,
        sector_data,
        fund_code,
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
        monthly_summary = pd.DataFrame([
            {
                "Month": month,
                "Total Contribution": result["total_contribution"],
                "Window Start": result["window_start"],
                "Window End": result["window_end"],
            }
            for month, result in historical_attribution.items()
        ])
        st.plotly_chart(
            dashboard_charts.build_monthly_contribution_chart(monthly_summary),
            use_container_width=True,
        )
        st.dataframe(
            monthly_summary.style.format(
                {"Total Contribution": "{:+.2f}pp"},
                na_rep="-",
            ),
            use_container_width=True,
            hide_index=True,
        )

        historical_months = list(historical_attribution.keys())
        selected_historical_month = st.selectbox(
            "Attribution month",
            historical_months,
            format_func=lambda month: pd.Timestamp(month).strftime("%b %Y"),
            key="historical_attribution_month",
        )
        selected_result = historical_attribution[selected_historical_month]
        top_month, bottom_month = attribution.top_bottom_contributors(
            selected_result["data"],
            n=5,
        )
        contributor_columns = [
            "Stock Name", "ISIN", "Current Weight", "Stock Return",
            "Contribution", "Sector", "Return Status",
        ]
        available_contributor_columns = [
            column for column in contributor_columns if column in selected_result["data"].columns
        ]
        top_col, bottom_col = st.columns(2)
        with top_col:
            st.markdown("**Top Contributors**")
            st.dataframe(
                top_month[available_contributor_columns].style.format(
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
        with bottom_col:
            st.markdown("**Bottom Contributors**")
            st.dataframe(
                bottom_month[available_contributor_columns].style.format(
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
                    pd.Timestamp(selected_historical_month).strftime("%b %Y"),
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
holdings_changes = rebalance.compute_holdings_changes(
    holdings,
    previous_holdings,
)
st.dataframe(
    holdings_changes.style.format(
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


# =============================================================================
# MONTHLY BEST & WORST CONTRIBUTORS
# =============================================================================

st.markdown("---")

st.markdown(
    "### Monthly Best & Worst Contributors"
)


st.caption(
    "Pick a month-end snapshot to calculate the "
    "stock-level contribution for that month."
)


contributor_dates = [
    d
    for d in available_dates
    if d != min(available_dates)
]


if not contributor_dates:

    st.info(
        "This fund only has one month-end snapshot "
        "so far - nothing to compare yet."
    )


else:

    contrib_month = st.selectbox(
        "Month",
        contributor_dates,
        format_func=lambda d:
            d.strftime("%b %Y"),
        key="contrib_month_select",
    )


    contrib_month_ts = pd.Timestamp(
        contrib_month
    )


    @st.cache_data(
        show_spinner=(
            "Fetching this month's stock price "
            "history from Yahoo Finance..."
        )
    )
    def _load_month_contributions(
        _fund_weightage,
        _mapping,
        fund_code,
        month_end_ts,
    ):

        fund_only = _fund_weightage[
            _fund_weightage["Fund Code"]
            == fund_code
        ]


        previous_snap = (
            data_loader.previous_snapshot(
                fund_only,
                fund_code,
                before_date=month_end_ts,
            )
        )


        previous_month_end = (
            previous_snap["Date"].iloc[0]
            if previous_snap is not None
            else None
        )


        contrib_df = (
            attribution.compute_stock_contributions_for_month(
                fund_only,
                _mapping,
                month_end=month_end_ts,
                previous_month_end=previous_month_end,
            )
        )


        return (
            contrib_df,
            previous_month_end,
        )


    if st.button(
        "Fetch contributors for this month"
    ):

        month_df, previous_month_end = (
            _load_month_contributions(
                fund_data.weightage,
                fund_data.mapping,
                fund_code,
                contrib_month_ts,
            )
        )


        st.session_state[
            "monthly_contrib_result"
        ] = (
            contrib_month_ts,
            month_df,
            previous_month_end,
        )


    result = st.session_state.get(
        "monthly_contrib_result"
    )


    if (
        result is not None
        and result[0] == contrib_month_ts
    ):

        (
            _,
            month_df,
            previous_month_end,
        ) = result


        if month_df.empty:

            st.info(
                "No monthly return could be "
                "computed for this snapshot."
            )


        else:

            st.caption(
                f"Stock returns calculated from "
                f"**{previous_month_end.date()}** "
                f"to "
                f"**{contrib_month_ts.date()}**."
            )


            failure_reason = (
                attribution.all_fetches_failed(
                    month_df
                )
            )


            if failure_reason:

                st.error(
                    f"Every holding's return fetch "
                    f"failed for this month "
                    f"(reason: {failure_reason})."
                )


            elif (
                "Return Status"
                in month_df.columns
                and month_df[
                    "Return Status"
                ]
                .astype(str)
                .str.startswith(
                    "Fetch Failed"
                )
                .any()
            ):

                n_failed = (
                    month_df[
                        "Return Status"
                    ]
                    .astype(str)
                    .str.startswith(
                        "Fetch Failed"
                    )
                    .sum()
                )


                st.warning(
                    f"{n_failed} of "
                    f"{len(month_df)} holding(s) "
                    f"show 0.00% because their "
                    f"return fetch failed."
                )


            if (
                "Return Status"
                in month_df.columns
                and month_df[
                    "Return Status"
                ]
                .astype(str)
                .str.contains(
                    "Verify",
                    na=False,
                )
                .any()
            ):

                flagged = month_df[
                    month_df[
                        "Return Status"
                    ]
                    .astype(str)
                    .str.contains(
                        "Verify",
                        na=False,
                    )
                ]


                st.warning(
                    f"{len(flagged)} holding(s) "
                    f"have a Stock Return that "
                    f"should be manually verified."
                )


            top5, bottom5 = (
                attribution.top_bottom_contributors(
                    month_df,
                    n=5,
                )
            )


            display_cols = [
                "Stock Name",
                "ISIN",
                "Current Weight",
                "Stock Return",
                "Contribution",
            ]


            if (
                "Return Status"
                in month_df.columns
            ):

                display_cols.append(
                    "Return Status"
                )


            for audit_col in (
                "Return Start Date",
                "Return Start Close",
                "Return End Date",
                "Return End Close",
            ):

                if audit_col in month_df.columns:

                    display_cols.append(
                        audit_col
                    )


            col_best, col_worst = (
                st.columns(2)
            )


            with col_best:

                st.markdown(
                    f"**Top 5 - "
                    f"{contrib_month_ts.strftime('%b %Y')}**"
                )


                st.altair_chart(
                    dashboard_charts.build_contributor_chart(
                        top5,
                        "#1F4E78",
                    ),
                    use_container_width=True,
                )


                st.dataframe(
                    top5[
                        display_cols
                    ].style.format(
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

                st.markdown(
                    f"**Bottom 5 - "
                    f"{contrib_month_ts.strftime('%b %Y')}**"
                )


                st.altair_chart(
                    dashboard_charts.build_contributor_chart(
                        bottom5,
                        "#C0392B",
                    ),
                    use_container_width=True,
                )


                st.dataframe(
                    bottom5[
                        display_cols
                    ].style.format(
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


    elif result is not None:

        st.caption(
            "Selected month has changed - click "
            "**Fetch contributors for this month** "
            "to load it."
        )


# =============================================================================
# EXCEL REPORT
# =============================================================================

st.markdown("---")


if st.button(
    "Generate Excel Report"
):

    with st.spinner(
        "Fetching stock returns and building report..."
    ):

        stock_returns = (
            attribution.fetch_stock_returns(
                holdings,
                start=s["Start Date"],
                end=s["End Date"],
            )
        )


        holdings_with_returns = (
            holdings.merge(
                stock_returns,
                on="ISIN",
                how="left",
            )
        )


        stock_contrib = (
            attribution.stock_contribution(
                holdings_with_returns
            )
        )


        sector_contrib = (
            attribution.sector_contribution(
                stock_contrib
            )
        )


        out_path = (
            report_generator.build_fund_report(
                fund_code=fund_code,
                fund_name=fund_name,
                perf=perf,
                period_perf=period_perf,
                holdings_enriched=holdings,
                stock_contrib=stock_contrib,
                sector_contrib=sector_contrib,
                rebalance_df=rebalance_df,
                threshold=threshold,
            )
        )


    with open(
        out_path,
        "rb",
    ) as f:

        st.download_button(
            "Download Fund_Report.xlsx",
            f,
            file_name=out_path.name,
        )


    st.success(
        f"Report generated: {out_path.name}"
    )