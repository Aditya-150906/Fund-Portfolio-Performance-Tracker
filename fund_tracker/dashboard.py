"""
dashboard.py
------------
The primary, hosted front-end over the same pipeline used by main.py.
"""

from pathlib import Path

import altair as alt
import pandas as pd
import plotly.express as px
import streamlit as st

import attribution
import config
import data_loader
import performance
import research
import rebalance
import report_generator
import security_master
import yahoo_fetch


st.set_page_config(
    page_title="Fund/Portfolio Performance Tracker",
    layout="wide",
)

st.title("Fund / Portfolio Performance Tracker")


# =============================================================================
# CHART HELPERS
# =============================================================================

def _nav_vs_benchmark_chart(daily: pd.DataFrame):
    """
    Dual-axis NAV vs Benchmark line chart.
    """

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


def _growth_chart(daily: pd.DataFrame):
    """
    Cumulative return growth chart.
    """

    df = (
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

    return df


# =============================================================================
# SIDEBAR - FILE MANAGEMENT
# =============================================================================

st.sidebar.header("Data files")


masters_configured = (
    config.has_nse_security_master()
    and config.has_bse_security_master()
)


with st.sidebar.expander(
    "Security Master files",
    expanded=not masters_configured,
):

    st.caption(
        "Static reference files used to resolve each holding's ISIN to a "
        "Yahoo Finance ticker."
    )

    st.text(
        "NSE Master: "
        + (
            config.get_nse_security_master().name
            if config.has_nse_security_master()
            else "not configured yet"
        )
    )

    st.text(
        "BSE Master: "
        + (
            config.get_bse_security_master().name
            if config.has_bse_security_master()
            else "not configured yet"
        )
    )

    nse_upload = st.file_uploader(
        "NSE Security Master (.csv/.xlsx)",
        type=["csv", "xlsx", "xls"],
        key="nse_master_upload",
    )

    if st.button(
        "Set NSE Security Master",
        disabled=nse_upload is None,
    ):

        dest = config.INPUT_DIR / nse_upload.name

        dest.write_bytes(
            nse_upload.getvalue()
        )

        problems = security_master.validate_nse_master_file(
            dest
        )

        if problems:

            st.error(
                "Couldn't use this file:\n"
                + "\n".join(
                    f"- {p}"
                    for p in problems
                )
            )

        else:

            config.set_nse_security_master(
                dest
            )

            security_master.reload_masters()

            st.cache_data.clear()

            st.success(
                f"NSE Security Master set to {nse_upload.name}."
            )

            st.rerun()


    bse_upload = st.file_uploader(
        "BSE Security Master (.csv/.xlsx)",
        type=["csv", "xlsx", "xls"],
        key="bse_master_upload",
    )

    if st.button(
        "Set BSE Security Master",
        disabled=bse_upload is None,
    ):

        dest = config.INPUT_DIR / bse_upload.name

        dest.write_bytes(
            bse_upload.getvalue()
        )

        problems = security_master.validate_bse_master_file(
            dest
        )

        if problems:

            st.error(
                "Couldn't use this file:\n"
                + "\n".join(
                    f"- {p}"
                    for p in problems
                )
            )

        else:

            config.set_bse_security_master(
                dest
            )

            security_master.reload_masters()

            st.cache_data.clear()

            st.success(
                f"BSE Security Master set to {bse_upload.name}."
            )

            st.rerun()


st.sidebar.markdown("---")


# =============================================================================
# CONFIGURED FUND FILES
# =============================================================================

with st.sidebar.expander(
    "Configured fund files",
    expanded=False,
):

    st.caption(
        "Re-checked every run - stays configured until removed."
    )

    st.markdown(
        "**Weightage file(s):**"
    )

    if config.has_weightage_files():

        for p in config.get_weightage_files():

            st.text(
                f"  {p.name}"
            )

    else:

        st.caption(
            "  none uploaded yet"
        )


    st.markdown(
        "**Daily NAV file(s):**"
    )

    if config.has_nav_files():

        for p in config.get_nav_files():

            st.text(
                f"  {p.name}"
            )

    else:

        st.caption(
            "  none uploaded yet"
        )


st.sidebar.markdown("---")


# =============================================================================
# ADD A FUND
# =============================================================================

with st.sidebar.expander(
    "Add a fund",
    expanded=not (
        config.has_weightage_files()
        and config.has_nav_files()
    ),
):

    st.caption(
        "Upload a new fund's Weightage and Daily NAV Excel files."
    )

    new_weightage_upload = st.file_uploader(
        "Weightage file (.xlsx)",
        type=["xlsx", "xls"],
        key="new_weightage_upload",
    )

    new_nav_upload = st.file_uploader(
        "Daily NAV file (.xlsx)",
        type=["xlsx", "xls"],
        key="new_nav_upload",
    )

    if st.button("Add fund"):

        if (
            not new_weightage_upload
            or not new_nav_upload
        ):

            st.sidebar.error(
                "Please choose both a Weightage file and a Daily NAV file."
            )

        else:

            dest_weightage = (
                config.INPUT_DIR
                / new_weightage_upload.name
            )

            dest_nav = (
                config.INPUT_DIR
                / new_nav_upload.name
            )

            dest_weightage.write_bytes(
                new_weightage_upload.getvalue()
            )

            dest_nav.write_bytes(
                new_nav_upload.getvalue()
            )

            problems = (
                data_loader.validate_weightage_file(
                    dest_weightage
                )
                + data_loader.validate_nav_file(
                    dest_nav
                )
            )

            if problems:

                st.sidebar.error(
                    "Couldn't add this fund:\n"
                    + "\n".join(
                        f"- {p}"
                        for p in problems
                    )
                )

            else:

                config.add_fund_files(
                    dest_weightage,
                    dest_nav,
                )

                st.cache_data.clear()

                st.sidebar.success(
                    f"Added {new_weightage_upload.name} / "
                    f"{new_nav_upload.name}."
                )

                st.rerun()


st.sidebar.markdown("---")


# =============================================================================
# REMOVE A FUND
# =============================================================================

with st.sidebar.expander(
    "Remove a fund",
    expanded=False,
):

    st.caption(
        "Un-registers a Weightage/Daily NAV file pair. "
        "The files themselves are not deleted."
    )

    if not (
        config.has_weightage_files()
        and config.has_nav_files()
    ):

        st.caption(
            "No fund files uploaded yet."
        )

        weightage_paths = []
        nav_paths = []

    else:

        weightage_paths = (
            config.get_weightage_files()
        )

        nav_paths = (
            config.get_nav_files()
        )


    if not weightage_paths and not nav_paths:

        pass

    elif (
        len(weightage_paths) <= 1
        and len(nav_paths) <= 1
    ):

        st.caption(
            "Only one fund file pair is configured."
        )

    elif len(weightage_paths) == len(nav_paths):

        for i, (
            w,
            n,
        ) in enumerate(
            zip(
                weightage_paths,
                nav_paths,
            )
        ):

            col1, col2 = st.columns(
                [4, 1]
            )

            col1.text(
                f"{w.name}\n{n.name}"
            )

            if col2.button(
                "Remove",
                key=f"remove_pair_{i}",
            ):

                config.remove_fund_files(
                    w,
                    n,
                )

                st.cache_data.clear()

                st.sidebar.success(
                    f"Removed {w.name} / {n.name}."
                )

                st.rerun()

    else:

        st.caption(
            "Weightage/NAV counts do not match."
        )

        st.markdown(
            "**Weightage file(s):**"
        )

        for w in weightage_paths:

            col1, col2 = st.columns(
                [4, 1]
            )

            col1.text(
                w.name
            )

            if col2.button(
                "Remove",
                key=f"remove_w_{w}",
            ):

                config.remove_weightage_file(
                    w
                )

                st.cache_data.clear()

                st.sidebar.success(
                    f"Removed {w.name}."
                )

                st.rerun()


        st.markdown(
            "**Daily NAV file(s):**"
        )

        for n in nav_paths:

            col1, col2 = st.columns(
                [4, 1]
            )

            col1.text(
                n.name
            )

            if col2.button(
                "Remove",
                key=f"remove_n_{n}",
            ):

                config.remove_nav_file(
                    n
                )

                st.cache_data.clear()

                st.sidebar.success(
                    f"Removed {n.name}."
                )

                st.rerun()


st.sidebar.markdown("---")


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

fund_code = st.sidebar.selectbox(
    "Fund",
    fund_codes,
)


available_dates = sorted(
    fund_data.weightage.loc[
        fund_data.weightage["Fund Code"]
        == fund_code,
        "Date",
    ]
    .dt.date
    .unique(),
    reverse=True,
)


snapshot_date = st.sidebar.selectbox(
    "Weightage snapshot (month-end)",
    available_dates,
    format_func=lambda d: d.strftime(
        "%b %Y"
    ),
)


threshold = st.sidebar.slider(
    "Rebalance drift threshold "
    "(percentage points)",
    1.0,
    10.0,
    config.DEFAULT_REBALANCE_THRESHOLD,
    0.5,
)


st.sidebar.caption(
    "Flags any holding whose weight has moved "
    "by more than this many percentage points "
    "versus the previous month-end snapshot."
)


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
                    _nav_vs_benchmark_chart(
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
                    _growth_chart(
                        period_daily
                    )
                )


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
    ]


    for column in percentage_columns:

        display_research[column] = (
            display_research[column].apply(
                lambda x:
                    f"{x:.2%}"
                    if pd.notna(x)
                    else "N/A"
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


    fig_returns = px.bar(
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


    fig_returns.update_yaxes(
        tickformat=".1%"
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


    fig_active = px.bar(
        active_chart_data,
        x="Fund",
        y="Active Return",
        title="Active Return by Fund",
        labels={
            "Active Return": "Active Return",
            "Fund": "Fund",
        },
    )


    fig_active.update_yaxes(
        tickformat=".1%"
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


    fig_risk = px.bar(
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


    fig_risk.update_yaxes(
        tickformat=".1%"
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


    def _contributor_bar_chart(
        df: pd.DataFrame,
        color: str,
    ):

        chart_df = df[
            [
                "Stock Name",
                "Contribution",
            ]
        ].copy()


        return (
            alt.Chart(
                chart_df
            )
            .mark_bar(
                color=color
            )
            .encode(
                x=alt.X(
                    "Contribution:Q",
                    title="Contribution (%)",
                    axis=alt.Axis(
                        format=".2f"
                    ),
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
            .properties(
                height=32
                * max(
                    len(chart_df),
                    1,
                )
            )
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
                    _contributor_bar_chart(
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
                    _contributor_bar_chart(
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