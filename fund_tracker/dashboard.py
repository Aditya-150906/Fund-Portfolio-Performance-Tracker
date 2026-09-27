"""
dashboard.py
------------
Main entry point and workspace orchestrator for the Fund Research Terminal.
"""

import pandas as pd
import streamlit as st

import config
import dashboard_charts
import dashboard_sections
import dashboard_sidebar
import dashboard_styles
import data_loader
import performance
import yahoo_fetch


# 1. Page Configuration
st.set_page_config(
    page_title="Fund Research Terminal",
    layout="wide",
    initial_sidebar_state="expanded",
)


# 2. Cached Data Loaders
@st.cache_data(show_spinner="Loading portfolio inputs...")
def _load_data():
    return data_loader.load_all()


@st.cache_data(show_spinner="Fetching sector mappings from Yahoo Finance...")
def _load_sectors(mapping):
    return yahoo_fetch.fetch_sector_data(mapping)


@st.cache_data(show_spinner="Fetching fundamental data from Yahoo Finance...")
def _load_fundamentals(mapping):
    return yahoo_fetch.fetch_fundamental_data(mapping)


# 3. Check Prerequisite Data Files
if not (
    config.has_weightage_files()
    and config.has_nav_files()
    and config.has_nse_security_master()
    and config.has_bse_security_master()
):
    tokens = dashboard_styles.get_theme_tokens(dark_mode=True)
    st.markdown(dashboard_styles.get_application_css(dark_mode=True), unsafe_allow_html=True)

    st.markdown(
        """
        <div class="fund-header" style="justify-content: center; padding: 2.5rem 1rem; text-align: center; border: 1px solid var(--border); border-radius: 4px;">
            <div>
                <span class="page-header-label" style="color: var(--accent);">SETUP REQUIRED</span>
                <h1 class="page-header-title" style="margin: 0.5rem 0 0.25rem 0;">Fund Research Application</h1>
                <p style="color: var(--text-muted); font-size: 0.85rem; max-width: 540px; margin: 0 auto;">
                    Configure both NSE and BSE Security Master files and register at least one fund's
                    Weightage + Daily NAV file pair using the sidebar controls.
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()


# 4. Load Data & Resolve Holdings
try:
    fund_data = _load_data()
except Exception as exc:
    st.error(f"Failed to load portfolio inputs: {exc}")
    st.stop()

sector_data = _load_sectors(fund_data.mapping)
fundamental_data = _load_fundamentals(fund_data.mapping)
fund_codes = data_loader.get_fund_codes(fund_data)


# 5. Render Sidebar Control Rail & Apply Theme
sidebar_state = dashboard_sidebar.render_sidebar_control_panel(fund_data)
fund_code = sidebar_state.fund_code
snapshot_date = sidebar_state.snapshot_date
threshold = sidebar_state.threshold
available_dates = sidebar_state.available_dates
dark_mode = sidebar_state.dark_mode

# Apply Design Tokens & Themes
theme_tokens = dashboard_styles.get_theme_tokens(dark_mode=dark_mode)
dashboard_charts.set_chart_theme(theme_tokens)
st.markdown(dashboard_styles.get_application_css(dark_mode=dark_mode), unsafe_allow_html=True)


# 6. Extract Portfolio Calculations for Active Fund
fund_weightage = data_loader.latest_snapshot(
    fund_data.weightage,
    fund_code,
    as_of=str(snapshot_date),
)
fund_name_val = fund_weightage["Fund Name"].iloc[0] if not fund_weightage.empty else None
fund_name = fund_name_val if pd.notna(fund_name_val) else fund_code

fund_nav = fund_data.nav[fund_data.nav["Fund Code"] == fund_code].copy()

holdings = fund_weightage.merge(
    fund_data.mapping[["ISIN", "Yahoo Ticker"]],
    on="ISIN",
    how="left",
)
holdings = yahoo_fetch.merge_sector_with_holdings(holdings, sector_data)

previous_holdings = data_loader.previous_snapshot(
    fund_data.weightage,
    fund_code,
    before_date=snapshot_date,
)

perf = performance.compute_fund_performance(fund_nav)
period_perf = performance.compute_multi_period_performance(fund_nav)


# 7. Persistent Top Navigation Bar
workspaces = ["Overview", "Performance", "Risk", "Portfolio", "Research", "Attribution"]

selected_workspace = st.radio(
    "Terminal Workspace",
    workspaces,
    index=0,
    horizontal=True,
    label_visibility="collapsed",
    key="active_workspace_nav",
)


# 8. Workspace Router
if selected_workspace == "Overview":
    dashboard_sections.render_overview_page(
        fund_data=fund_data,
        fund_code=fund_code,
        fund_name=fund_name,
        snapshot_date=snapshot_date,
        perf=perf,
        period_perf=period_perf,
        holdings=holdings,
        previous_holdings=previous_holdings,
        sector_data=sector_data,
        fundamental_data=fundamental_data,
        threshold=threshold,
    )

elif selected_workspace == "Performance":
    dashboard_sections.render_performance_page(
        period_perf=period_perf,
        fund_name=fund_name,
        fund_code=fund_code,
    )

elif selected_workspace == "Risk":
    dashboard_sections.render_risk_page(
        perf=perf,
        period_perf=period_perf,
        fund_name=fund_name,
        fund_code=fund_code,
    )

elif selected_workspace == "Portfolio":
    dashboard_sections.render_portfolio_page(
        fund_data=fund_data,
        fund_code=fund_code,
        fund_name=fund_name,
        snapshot_date=snapshot_date,
        holdings=holdings,
        previous_holdings=previous_holdings,
        sector_data=sector_data,
        fundamental_data=fundamental_data,
        fund_codes=fund_codes,
        threshold=threshold,
    )

elif selected_workspace == "Research":
    dashboard_sections.render_research_page(
        fund_data=fund_data,
        fundamental_data=fundamental_data,
        fund_codes=fund_codes,
    )

elif selected_workspace == "Attribution":
    dashboard_sections.render_attribution_page(
        fund_data=fund_data,
        fund_code=fund_code,
        fund_name=fund_name,
        snapshot_date=snapshot_date,
        holdings=holdings,
        previous_holdings=previous_holdings,
        sector_data=sector_data,
        available_dates=available_dates,
        perf=perf,
        period_perf=period_perf,
        threshold=threshold,
    )
