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
import dashboard_sections
import dashboard_sidebar
import performance
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


perf = performance.compute_fund_performance(fund_nav)
s = perf["summary"]
period_perf = performance.compute_multi_period_performance(fund_nav)
dashboard_sections.render_performance_section(period_perf)
dashboard_sections.render_risk_section(perf, fund_name, fund_code)
research_df = dashboard_sections.render_research_section(fund_data)


detail_state = dashboard_sections.render_fund_research_section(fund_data)
detail_fund = detail_state.detail_fund
detail_weightage = detail_state.detail_weightage
dashboard_sections.render_portfolio_analytics_section(
    fund_data,
    detail_fund,
    fundamental_data,
    fund_codes,
)


previous_holdings = (
    data_loader.previous_snapshot(
        fund_data.weightage,
        fund_code,
        before_date=snapshot_date,
    )
)

dashboard_sections.render_fundamental_section(
    detail_weightage,
    fund_data.mapping,
    fundamental_data,
)
rebalance_df = dashboard_sections.render_holdings_changes_section(
    holdings,
    previous_holdings,
    threshold,
)


dashboard_sections.render_historical_attribution_section(
    fund_data.weightage,
    fund_data.mapping,
    sector_data,
    fund_code,
    holdings,
    previous_holdings,
)


dashboard_sections.render_attribution_section(
    fund_data.weightage,
    fund_data.mapping,
    fund_code,
    available_dates,
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