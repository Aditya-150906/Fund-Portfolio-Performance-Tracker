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
import dashboard_charts
import dashboard_sidebar
import performance
import report_generator
import yahoo_fetch


st.set_page_config(
    page_title="Fund/Portfolio Performance Tracker",
    layout="wide",
)

appearance_theme = dashboard_sidebar.render_appearance_control()
dark_theme = appearance_theme == "Dark"
theme = {
    "background": "#11161C" if dark_theme else "#F7F8FA",
    "surface": "#171D24" if dark_theme else "#FFFFFF",
    "text": "#E8EDF2" if dark_theme else "#17202A",
    "muted": "#9AA6B2" if dark_theme else "#66717C",
    "border": "#2A333D" if dark_theme else "#DDE2E7",
    "navy": "#8FB4D6" if dark_theme else "#17324D",
    "soft": "#1D252E" if dark_theme else "#F5F7FA",
    "green": "#58C7A5" if dark_theme else "#147D64",
    "red": "#F07C7C" if dark_theme else "#B34A4A",
}
dashboard_charts.set_chart_theme(theme)

theme_styles = """
    <style>
    :root {
        --app-background: __BACKGROUND__;
        --surface: __SURFACE__;
        --primary-text: __TEXT__;
        --muted-text: __MUTED__;
        --border: __BORDER__;
        --navy: __NAVY__;
        --slate: __MUTED__;
        --line: __BORDER__;
        --soft: __SOFT__;
        --green: __GREEN__;
        --red: __RED__;
        --accent: __NAVY__;
    }
    html, body, [data-testid="stAppViewContainer"],
    [data-testid="stAppViewContainer"] > .main {
        background-color: var(--app-background);
        color: var(--primary-text);
    }
    [data-testid="stSidebar"] {
        background-color: var(--surface);
        border-right: 1px solid var(--border);
    }
    [data-testid="stSidebar"] * {
        color: var(--primary-text);
    }
    header[data-testid="stHeader"],
    [data-testid="stToolbar"] {
        background-color: var(--surface);
    }
    header[data-testid="stHeader"] button,
    [data-testid="stToolbar"] button {
        color: var(--primary-text);
    }
    [data-testid="stWidgetLabel"] p,
    [data-testid="stCaptionContainer"] p,
    [data-testid="stCaptionContainer"] *,
    .stCaption,
    .stMarkdown p {
        color: var(--muted-text);
    }
    [data-testid="stMetricLabel"] {
        color: var(--muted-text);
    }
    [data-testid="stMetricLabel"] * {
        color: var(--muted-text);
    }
    [data-testid="stMetricValue"] {
        color: var(--primary-text);
    }
    [data-testid="stMetricValue"] * {
        color: var(--primary-text);
    }
    [data-testid="stMetricDelta"] {
        color: var(--green);
    }
    [data-testid="stMetricDelta"] * {
        color: inherit;
    }
    [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: var(--surface);
        border-color: var(--border);
    }
    [data-testid="stDataFrame"] {
        border: 1px solid var(--border);
        border-radius: 6px;
    }
    [data-testid="stPlotlyChart"],
    [data-testid="stVegaLiteChart"] {
        background-color: var(--surface);
        border: 1px solid var(--border);
        border-radius: 6px;
        padding: 0.25rem;
    }
    .stSelectbox > div > div,
    .stMultiSelect > div > div,
    .stNumberInput > div > div,
    .stTextInput > div > div {
        background-color: var(--surface);
        border-color: var(--border);
        color: var(--primary-text);
    }
    [data-baseweb="select"] *,
    [data-baseweb="input"] input,
    [data-baseweb="textarea"] textarea {
        color: var(--primary-text);
    }
    [data-baseweb="select"] > div,
    [data-baseweb="input"] > div,
    [data-baseweb="textarea"] > div {
        background-color: var(--surface);
        border-color: var(--border);
    }
    [data-baseweb="select"]:focus-within > div,
    [data-baseweb="input"]:focus-within > div,
    [data-baseweb="textarea"]:focus-within > div {
        border-color: var(--accent);
        box-shadow: 0 0 0 1px var(--accent);
    }
    [data-baseweb="popover"] {
        background-color: var(--surface);
    }
    [data-baseweb="popover"] * {
        color: var(--primary-text);
    }
    [data-testid="stExpander"] {
        background-color: var(--surface);
        border-color: var(--border);
    }
    [data-testid="stExpander"] summary,
    [data-testid="stExpander"] summary * {
        color: var(--primary-text);
    }
    button[kind="secondary"],
    button[kind="primary"] {
        color: var(--primary-text);
        border-color: var(--border);
    }
    button[kind="secondary"]:focus-visible,
    button[kind="primary"]:focus-visible {
        border-color: var(--accent);
        box-shadow: 0 0 0 1px var(--accent);
        outline: none;
    }
    [data-baseweb="tab-list"] {
        border-color: var(--border);
    }
    [data-baseweb="tab"] {
        color: var(--muted-text);
    }
    [data-baseweb="tab"] p {
        color: inherit;
    }
    [data-baseweb="tab"][aria-selected="true"] {
        color: var(--primary-text);
    }
    [data-baseweb="tab-highlight"] {
        background-color: var(--accent);
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1500px;
    }
    .app-header {
        border-bottom: 1px solid var(--line);
        padding: 0.25rem 0 1.25rem 0;
        margin-bottom: 1.25rem;
    }
    .app-header h1 {
        color: var(--navy);
        font-size: 2rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        margin: 0;
    }
    .app-header p {
        color: var(--slate);
        font-size: 0.95rem;
        margin: 0.35rem 0 0;
    }
    .portfolio-context {
        background: var(--soft);
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 0.85rem 1rem;
        margin: 0.25rem 0 1rem;
    }
    .portfolio-context-label {
        color: var(--slate);
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }
    .portfolio-context-value {
        color: var(--navy);
        font-size: 1.15rem;
        font-weight: 650;
        margin-top: 0.2rem;
    }
    .portfolio-context-meta {
        color: var(--slate);
        font-size: 0.86rem;
        margin-top: 0.2rem;
    }
    .section-kicker {
        color: var(--slate);
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin: 0 0 0.35rem;
    }
    </style>
"""

st.markdown(
    theme_styles
    .replace("__BACKGROUND__", theme["background"])
    .replace("__SURFACE__", theme["surface"])
    .replace("__TEXT__", theme["text"])
    .replace("__MUTED__", theme["muted"])
    .replace("__BORDER__", theme["border"])
    .replace("__NAVY__", theme["navy"])
    .replace("__SOFT__", theme["soft"])
    .replace("__GREEN__", theme["green"])
    .replace("__RED__", theme["red"])
    + """
    <div class="app-header">
        <h1>Fund / Portfolio Performance Tracker</h1>
        <p>Performance, risk, portfolio structure, attribution, and holdings research in one view.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


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
def _load_sectors(mapping):

    return yahoo_fetch.fetch_sector_data(
        mapping
    )


@st.cache_data(
    show_spinner="Fetching fundamental data from Yahoo Finance..."
)
def _load_fundamentals(mapping):

    return yahoo_fetch.fetch_fundamental_data(
        mapping
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


st.markdown(
    f"""
    <div class="portfolio-context">
        <div class="portfolio-context-label">Active Portfolio</div>
        <div class="portfolio-context-value">{fund_name}</div>
        <div class="portfolio-context-meta">
            Fund code: {fund_code} &nbsp;&bull;&nbsp;
            Snapshot: {snapshot_date.strftime('%B %Y')}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
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
st.markdown('<div class="section-kicker">Portfolio Snapshot</div>', unsafe_allow_html=True)
with st.container(border=True):
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    absolute_return = s.get("Absolute Return")
    volatility = s.get("Volatility")
    sharpe_ratio = s.get("Sharpe Ratio")
    maximum_drawdown = s.get("Maximum Drawdown")
    kpi1.metric(
        "Return",
        f"{absolute_return:.2%}" if pd.notna(absolute_return) else "N/A",
    )
    kpi2.metric(
        "Volatility",
        f"{volatility:.2%}" if pd.notna(volatility) else "N/A",
    )
    kpi3.metric(
        "Sharpe Ratio",
        f"{sharpe_ratio:.2f}" if pd.notna(sharpe_ratio) else "N/A",
    )
    kpi4.metric(
        "Maximum Drawdown",
        f"{maximum_drawdown:.2%}" if pd.notna(maximum_drawdown) else "N/A",
    )

with st.container(border=True):
    dashboard_sections.render_performance_section(period_perf)

with st.container(border=True):
    dashboard_sections.render_risk_section(perf, fund_name, fund_code)

research_df = dashboard_sections.render_research_section(fund_data)


with st.container(border=True):
    detail_state = dashboard_sections.render_fund_research_section(fund_data)
detail_fund = detail_state.detail_fund
detail_weightage = detail_state.detail_weightage
with st.container(border=True):
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

with st.container(border=True):
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


with st.container(border=True):
    historical_attribution = dashboard_sections.render_historical_attribution_section(
        fund_data.weightage,
        fund_data.mapping,
        sector_data,
        fund_code,
        holdings,
        previous_holdings,
    )


with st.container(border=True):
    dashboard_sections.render_attribution_section(
        fund_data.weightage,
        fund_data.mapping,
        sector_data,
        fund_code,
        available_dates,
        historical_attribution,
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