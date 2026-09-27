"""
dashboard_sections.py
---------------------
Modular analytical workspaces for the Fund Research Terminal.
Each workspace has a custom visual composition designed specifically
for institutional investment analysis.
"""

import numpy as np
import pandas as pd
import streamlit as st

import attribution
import config
import dashboard_charts
import data_loader
import performance
import rebalance
import report_generator
import research


# =============================================================================
# DATA FORMATTING & TEST-CONTRACT HELPERS
# =============================================================================

def build_research_display_frame(research_df: pd.DataFrame) -> pd.DataFrame:
    """Format research dataframe with consistent financial notation."""
    display_df = research_df.copy()
    pct_cols = [
        "Absolute Return", "CAGR", "Benchmark Return", "Active Return",
        "Alpha", "Tracking Error", "Max Drawdown", "Volatility",
        "Benchmark Volatility", "Downside Deviation", "Jensen's Alpha",
    ]
    dec_cols = [
        "Sharpe Ratio", "Sortino Ratio", "Beta", "Information Ratio",
    ]
    for col in pct_cols:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(
                lambda val: f"{val:.2%}" if pd.notna(val) else "—"
            )
    for col in dec_cols:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(
                lambda val: f"{val:.2f}" if pd.notna(val) else "—"
            )
    return display_df


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
    """Merge and format fundamental data for the screener view."""
    merged = detail_weightage.merge(
        mapping[["ISIN", "Yahoo Ticker"]],
        on="ISIN",
        how="left",
    )
    if fundamental_data is not None and not fundamental_data.empty:
        merged = merged.merge(
            fundamental_data,
            on=["ISIN", "Yahoo Ticker"],
            how="left",
        )
    if "Is Cash" in merged.columns:
        merged = merged[~merged["Is Cash"]].copy()

    cols = [
        "Fund Name", "Stock Name", "ISIN", "Yahoo Ticker", "Current Weight",
        "Market Cap", "PE Ratio", "PB Ratio", "ROE", "Dividend Yield",
        "Debt to Equity",
    ]
    available_cols = [c for c in cols if c in merged.columns]
    display_df = merged[available_cols].copy().rename(
        columns={
            "Fund Name": "Fund",
            "Stock Name": "Company",
            "Current Weight": "Weight",
            "PE Ratio": "P/E",
            "PB Ratio": "P/B",
            "Debt to Equity": "Debt / Equity",
        }
    )
    if "Yahoo Ticker" in display_df.columns:
        display_df["Yahoo Ticker"] = display_df["Yahoo Ticker"].fillna("—")
    if "ISIN" in display_df.columns:
        display_df["ISIN"] = display_df["ISIN"].fillna("—")

    if "Weight" in display_df.columns:
        display_df["Weight"] = display_df["Weight"].map(lambda v: f"{v:.2f}%" if pd.notna(v) else "—")
    if "Market Cap" in display_df.columns:
        display_df["Market Cap"] = display_df["Market Cap"].map(lambda v: f"{v / 1e12:.2f} T" if pd.notna(v) and v > 0 else "—")
    if "P/E" in display_df.columns:
        display_df["P/E"] = display_df["P/E"].map(lambda v: f"{v:.2f}" if pd.notna(v) else "—")
    if "P/B" in display_df.columns:
        display_df["P/B"] = display_df["P/B"].map(lambda v: f"{v:.2f}" if pd.notna(v) else "—")
    if "ROE" in display_df.columns:
        display_df["ROE"] = display_df["ROE"].map(lambda v: f"{v:.2%}" if pd.notna(v) else "—")
    if "Dividend Yield" in display_df.columns:
        display_df["Dividend Yield"] = display_df["Dividend Yield"].map(lambda v: f"{v:.2%}" if pd.notna(v) and v <= 1 else (f"{v:.2f}%" if pd.notna(v) else "—"))
    if "Debt / Equity" in display_df.columns:
        display_df["Debt / Equity"] = display_df["Debt / Equity"].map(lambda v: f"{v:.2f}" if pd.notna(v) else "—")

    return display_df


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


def select_historical_attribution_month(
    monthly_attribution: dict | None,
    requested_month,
) -> dict | None:
    """Return a stored monthly attribution result without recalculating it."""
    if not monthly_attribution or requested_month is None:
        return None

    requested_timestamp = pd.Timestamp(requested_month)
    for month, result in monthly_attribution.items():
        if pd.Timestamp(month) == requested_timestamp:
            return result
    return None


def prepare_attribution_weightage(
    weightage: pd.DataFrame,
    sector_data: pd.DataFrame | None,
    fund_code: str,
) -> pd.DataFrame:
    """Prepare one fund's attribution input with the same sector enrichment everywhere."""
    prepared = weightage[weightage["Fund Code"] == fund_code].copy()
    if sector_data is None or sector_data.empty:
        return prepared

    sector_columns = [
        column for column in ["ISIN", "Sector"] if column in sector_data.columns
    ]
    if len(sector_columns) != 2:
        return prepared

    sector_lookup = sector_data[sector_columns].drop_duplicates("ISIN")
    if "Sector" in prepared.columns:
        prepared = prepared.drop(columns=["Sector"])
    return prepared.merge(sector_lookup, on="ISIN", how="left")


def build_attribution_cache_token(*frames: pd.DataFrame | None) -> str:
    """Build a compact content token for cached attribution inputs."""
    parts = []
    for frame in frames:
        if frame is None:
            parts.append("none")
            continue
        if frame.empty:
            parts.append(f"empty:{tuple(frame.columns)}")
            continue
        digest = pd.util.hash_pandas_object(frame, index=True).sum()
        parts.append(f"{frame.shape}:{tuple(frame.columns)}:{int(digest)}")
    return "|".join(parts)


def build_holdings_change_display_frame(holdings_changes: pd.DataFrame) -> pd.DataFrame:
    """Return a display copy of the existing holdings-change result."""
    return holdings_changes.copy()


# =============================================================================
# 1. OVERVIEW WORKSPACE (LANDING EXPERIENCE)
# =============================================================================

def render_overview_page(
    fund_data,
    fund_code: str,
    fund_name: str,
    snapshot_date: object,
    perf: dict,
    period_perf: dict,
    holdings: pd.DataFrame,
    previous_holdings: pd.DataFrame | None,
    sector_data: pd.DataFrame,
    fundamental_data: pd.DataFrame,
    threshold: float,
) -> None:
    """Render the executive Overview workspace with high visual hierarchy."""
    s = perf["summary"]
    daily = perf["daily"]

    latest_nav = s.get("Portfolio NAV (End)", 0.0)
    abs_return = s.get("Absolute Return", np.nan)
    cagr_val = s.get("CAGR", np.nan)
    active_ret = s.get("Active Return", np.nan)
    sharpe = s.get("Sharpe Ratio", np.nan)
    vol = s.get("Volatility", np.nan)
    max_dd = s.get("Maximum Drawdown", np.nan)

    # 1. Top Header Bar
    st.markdown(
        f"""
        <div class="fund-header">
            <div class="fund-header-name">{fund_name}</div>
            <div class="fund-header-meta">
                <span class="fund-header-chip">CODE: <b>{fund_code}</b></span>
                <span class="fund-header-chip">AS OF: <b>{snapshot_date.strftime('%d %b %Y')}</b></span>
                <span class="fund-header-chip">BENCHMARK: <b>NIFTY 500</b></span>
            </div>
        </div>
        <hr class="thin-divider" style="margin-top: 0; margin-bottom: 1.5rem;" />
        """,
        unsafe_allow_html=True,
    )

    # 2. Key Metrics Presentation (Typography driven)
    col_hero, col_metrics = st.columns([1.0, 2.2])

    with col_hero:
        ret_str = f"{abs_return:+.2%}" if pd.notna(abs_return) else "—"
        ret_color = "color: var(--positive);" if pd.notna(abs_return) and abs_return >= 0 else "color: var(--negative);"

        # Check for both nan string and actual nan float
        is_valid_cagr = pd.notna(cagr_val) and str(cagr_val).lower() != "nan"
        cagr_str = f"{cagr_val:.2%} CAGR" if is_valid_cagr else "CAGR: N/A"

        nav_str = f"₹{latest_nav:,.2f}" if pd.notna(latest_nav) else "N/A"

        st.markdown(
            f"""
            <div class="hero-stat">
                <div class="hero-stat-label">Net Asset Value</div>
                <div class="hero-stat-value">{nav_str}</div>
                <div class="hero-stat-delta" style="{ret_color}">
                    {ret_str} <span style="color: var(--text-muted); font-weight: 400; font-size: 0.75rem;">({cagr_str})</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_metrics:
        act_str = f"{active_ret:+.2%}" if pd.notna(active_ret) else "—"
        act_color = "color: var(--positive);" if pd.notna(active_ret) and active_ret >= 0 else "color: var(--negative);"
        vol_str = f"{vol:.2%}" if pd.notna(vol) else "—"
        sharpe_str = f"{sharpe:.2f}" if pd.notna(sharpe) else "—"
        dd_str = f"{max_dd:.2%}" if pd.notna(max_dd) else "—"

        metrics_html = (
            '<div class="stat-row" style="padding-top: 1.5rem; margin-left: 1rem;">'
            f'<div class="stat-item">'
            f'<div class="stat-item-label">Active Return</div>'
            f'<div class="stat-item-value" style="{act_color}">{act_str}</div>'
            f'</div>'
            f'<div class="stat-item">'
            f'<div class="stat-item-label">Volatility (Ann)</div>'
            f'<div class="stat-item-value">{vol_str}</div>'
            f'</div>'
            f'<div class="stat-item">'
            f'<div class="stat-item-label">Sharpe Ratio</div>'
            f'<div class="stat-item-value">{sharpe_str}</div>'
            f'</div>'
            f'<div class="stat-item">'
            f'<div class="stat-item-label">Max Drawdown</div>'
            f'<div class="stat-item-value" style="color: var(--negative);">{dd_str}</div>'
            f'</div>'
            '</div>'
        )
        st.markdown(metrics_html, unsafe_allow_html=True)

    st.markdown("<div style='height: 0.75rem;'></div>", unsafe_allow_html=True)

    # 3. Main Centerpiece NAV vs Benchmark Chart
    col_chart, col_ledger = st.columns([2.1, 1.1])

    with col_chart:
        st.markdown('<div class="section-label">Historical Compounding</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-title" style="font-size: 1.15rem; margin-bottom: 0.5rem;">NAV vs Benchmark Trajectory</div>', unsafe_allow_html=True)
        st.altair_chart(dashboard_charts.build_nav_vs_benchmark_chart(daily), use_container_width=True)

    with col_ledger:
        st.markdown('<div class="section-label">Holdings Activity</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-title" style="font-size: 1.15rem; margin-bottom: 0.5rem;">What Changed</div>', unsafe_allow_html=True)

        changes = rebalance.compute_holdings_changes(holdings, previous_holdings)
        top_inc = changes[changes["Change Type"] == "Increased"].sort_values("Weight Change", ascending=False).head(3)
        top_dec = changes[changes["Change Type"] == "Reduced"].sort_values("Weight Change", ascending=True).head(3)
        new_pos = changes[changes["Change Type"] == "New"].head(2)
        exited_pos = changes[changes["Change Type"] == "Exited"].head(2)

        rows_html = ""
        for _, r in top_inc.iterrows():
            name = r["Stock Name"] if pd.notna(r["Stock Name"]) else "Unknown"
            rows_html += f'<div class="ledger-row"><span class="ledger-name">▲ {name}</span><span class="ledger-val" style="color: var(--positive);">{r["Weight Change"]:+.2f} pp</span></div>'
        for _, r in top_dec.iterrows():
            name = r["Stock Name"] if pd.notna(r["Stock Name"]) else "Unknown"
            rows_html += f'<div class="ledger-row"><span class="ledger-name">▼ {name}</span><span class="ledger-val" style="color: var(--negative);">{r["Weight Change"]:+.2f} pp</span></div>'
        for _, r in new_pos.iterrows():
            name = r["Stock Name"] if pd.notna(r["Stock Name"]) else "Unknown"
            rows_html += f'<div class="ledger-row"><span class="ledger-name"><span style="color: var(--accent); font-weight:700;">NEW</span> {name}</span><span class="ledger-val" style="color: var(--positive);">{r["Current Weight"]:.2f}%</span></div>'
        for _, r in exited_pos.iterrows():
            name = r["Stock Name"] if pd.notna(r["Stock Name"]) else "Unknown"
            rows_html += f'<div class="ledger-row"><span class="ledger-name"><span style="color: var(--negative); font-weight:700;">EXIT</span> {name}</span><span class="ledger-val" style="color: var(--negative);">0.00%</span></div>'

        if not rows_html:
            rows_html = '<div class="ledger-row"><span class="ledger-name">Earliest snapshot available; no prior baseline.</span></div>'

        st.markdown(
            f"""
            <div class="ledger-container">
                <div class="ledger-header">
                    <span class="ledger-title">Significant Position Shifts</span>
                    <span style="font-size: 0.7rem; color: var(--text-muted); font-family: 'JetBrains Mono', monospace;">MoM</span>
                </div>
                {rows_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 0.75rem;'></div>", unsafe_allow_html=True)

    # 4. Concentration & Structure Breakdown
    analytics = research.build_portfolio_analytics(fund_data, fund_code, fundamental_data=fundamental_data)
    conc = analytics.get("Concentration", {})

    c_top, c_sec = st.columns([1.5, 1.5])
    with c_top:
        st.markdown('<div class="section-label">Portfolio Structure</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-title" style="font-size: 1.15rem; margin-bottom: 0.5rem;">Top 10 Holdings</div>', unsafe_allow_html=True)
        top10_df = holdings[~holdings["Is Cash"]].sort_values("Current Weight", ascending=False).head(10)
        st.plotly_chart(dashboard_charts.build_top_holdings_bar_chart(top10_df), use_container_width=True, key="overview_top_holdings")

    with c_sec:
        st.markdown('<div class="section-label">Sector Exposure</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-title" style="font-size: 1.15rem; margin-bottom: 0.5rem;">Sector Allocation Breakdown</div>', unsafe_allow_html=True)
        sec_df = analytics.get("Sector Allocation", pd.DataFrame())
        donut = dashboard_charts.build_sector_allocation_donut_chart(sec_df)
        if donut is not None:
            st.plotly_chart(donut, use_container_width=True, key="overview_sector_allocation")
        else:
            st.info("Sector data unavailable.")


# =============================================================================
# 2. PERFORMANCE WORKSPACE
# =============================================================================

def render_performance_page(period_perf: dict, fund_name: str, fund_code: str) -> None:
    """Render dedicated Performance Workspace with returns ledger, chart, and period breakdown."""
    st.markdown(
        f"""
        <div class="page-header">
            <div class="page-header-label">PERFORMANCE</div>
            <h1 class="page-header-title">Historical Returns — {fund_name} ({fund_code})</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )

    period_tabs = st.tabs(performance.PERIOD_ORDER)

    for label, tab in zip(performance.PERIOD_ORDER, period_tabs):
        with tab:
            ps = period_perf[label]
            if not ps["Available"]:
                st.info(f"{label}: {ps['Reason']}.")
                continue

            if ps["Truncated"]:
                st.caption(f"Fund history only goes back to {ps['Window Start'].date()} for this window.")

            # Metric Tiles for this period
            c1, c2, c3, c4, c5 = st.columns(5)

            abs_ret = ps.get("Absolute Return")
            c1.metric("Absolute Return", f"{abs_ret:.2%}" if pd.notna(abs_ret) else "N/A")

            if ps.get("CAGR Annualised", True):
                cagr_val = ps.get('CAGR')
                is_valid_cagr = pd.notna(cagr_val) and str(cagr_val).lower() != "nan"
                c2.metric("CAGR", f"{cagr_val:.2%}" if is_valid_cagr else "N/A")
                alpha_val = ps.get("Alpha")
                c3.metric("Alpha", f"{alpha_val:.2%}" if pd.notna(alpha_val) else "N/A")
            else:
                c2.metric("CAGR", "N/A", help="Window under 1 year")
                c3.metric("Alpha", "N/A", help="Window under 1 year")

            bench_ret = ps.get("Benchmark Return")
            c4.metric("Benchmark Return", f"{bench_ret:.2%}" if pd.notna(bench_ret) else "N/A")

            max_dd = ps.get("Maximum Drawdown")
            c5.metric("Max Drawdown", f"{max_dd:.2%}" if pd.notna(max_dd) else "N/A")

            period_daily = ps["Daily"]
            if not period_daily.empty:
                st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)
                col_left, col_right = st.columns(2)
                with col_left:
                    st.caption(f"NAV vs Benchmark ({label})")
                    st.altair_chart(dashboard_charts.build_nav_vs_benchmark_chart(period_daily), use_container_width=True)
                with col_right:
                    st.caption(f"Cumulative Compounding Growth ({label})")
                    st.plotly_chart(
                        dashboard_charts.build_growth_plotly_chart(period_daily),
                        use_container_width=True,
                        key=f"performance_growth_{label}",
                    )


# =============================================================================
# 3. RISK WORKSPACE
# =============================================================================

def render_risk_page(perf: dict, period_perf: dict, fund_name: str, fund_code: str) -> None:
    """Render dedicated Risk & Volatility Workspace."""
    s = perf["summary"]
    daily = perf["daily"]

    st.markdown(
        f"""
        <div class="page-header">
            <div class="page-header-label">RISK PROFILE</div>
            <h1 class="page-header-title">Drawdown & Volatility Analysis — {fund_name}</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 1. Risk Matrix Strip
    vol_str = f"{s.get('Volatility', np.nan):.2%}" if pd.notna(s.get('Volatility')) else "—"
    bench_vol = f"{s.get('Benchmark Volatility', np.nan):.2%}" if pd.notna(s.get('Benchmark Volatility')) else "—"
    sharpe_str = f"{s.get('Sharpe Ratio', np.nan):.2f}" if pd.notna(s.get('Sharpe Ratio')) else "—"
    sortino_str = f"{s.get('Sortino Ratio', np.nan):.2f}" if pd.notna(s.get('Sortino Ratio')) else "—"
    down_dev = f"{s.get('Downside Deviation', np.nan):.2%}" if pd.notna(s.get('Downside Deviation')) else "—"
    beta_str = f"{s.get('Beta', np.nan):.2f}" if pd.notna(s.get('Beta')) else "—"
    j_alpha = f"{s.get('Jensen\'s Alpha', np.nan):.2%}" if pd.notna(s.get('Jensen\'s Alpha')) else "—"
    max_dd = f"{s.get('Maximum Drawdown', np.nan):.2%}" if pd.notna(s.get('Maximum Drawdown')) else "—"

    st.markdown(
        f"""
        <div class="risk-matrix">
            <div class="risk-matrix-cell">
                <div class="risk-matrix-label">Portfolio Volatility</div>
                <div class="risk-matrix-value">{vol_str}</div>
            </div>
            <div class="risk-matrix-cell">
                <div class="risk-matrix-label">Benchmark Volatility</div>
                <div class="risk-matrix-value">{bench_vol}</div>
            </div>
            <div class="risk-matrix-cell">
                <div class="risk-matrix-label">Sharpe Ratio</div>
                <div class="risk-matrix-value">{sharpe_str}</div>
            </div>
            <div class="risk-matrix-cell">
                <div class="risk-matrix-label">Sortino Ratio</div>
                <div class="risk-matrix-value">{sortino_str}</div>
            </div>
            <div class="risk-matrix-cell">
                <div class="risk-matrix-label">Downside Deviation</div>
                <div class="risk-matrix-value">{down_dev}</div>
            </div>
            <div class="risk-matrix-cell">
                <div class="risk-matrix-label">Portfolio Beta</div>
                <div class="risk-matrix-value">{beta_str}</div>
            </div>
            <div class="risk-matrix-cell">
                <div class="risk-matrix-label">Jensen's Alpha</div>
                <div class="risk-matrix-value">{j_alpha}</div>
            </div>
            <div class="risk-matrix-cell">
                <div class="risk-matrix-label">Maximum Drawdown</div>
                <div class="risk-matrix-value" style="color: var(--negative);">{max_dd}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height: 0.75rem;'></div>", unsafe_allow_html=True)

    # 2. Rolling Metrics Side by Side
    col_roll_vol, col_roll_sharpe = st.columns(2)
    with col_roll_vol:
        st.caption("126-Day Rolling Annualized Volatility")
        st.altair_chart(dashboard_charts.build_rolling_metric_chart(daily, "Rolling Volatility", "#D29922"), use_container_width=True)

    with col_roll_sharpe:
        st.caption("126-Day Rolling Sharpe Ratio")
        st.altair_chart(dashboard_charts.build_rolling_metric_chart(daily, "Rolling Sharpe", "#2EA043"), use_container_width=True)

    st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

    # 3. Full-width Drawdown Area Chart
    st.caption("Underwater Drawdown Profile (Peak to Trough)")
    st.altair_chart(dashboard_charts.build_drawdown_chart(daily), use_container_width=True)


# =============================================================================
# 4. PORTFOLIO WORKSPACE
# =============================================================================

def render_portfolio_page(
    fund_data,
    fund_code: str,
    fund_name: str,
    snapshot_date: object,
    holdings: pd.DataFrame,
    previous_holdings: pd.DataFrame | None,
    sector_data: pd.DataFrame,
    fundamental_data: pd.DataFrame,
    fund_codes: list,
    threshold: float,
) -> None:
    """Render Holdings Terminal, Drift Analysis, and Concentration breakdown."""
    analytics = research.build_portfolio_analytics(fund_data, fund_code, as_of=str(snapshot_date), fundamental_data=fundamental_data)
    conc = analytics.get("Concentration", {})

    st.markdown(
        f"""
        <div class="page-header">
            <div class="page-header-label">PORTFOLIO HOLDINGS</div>
            <h1 class="page-header-title">Portfolio Composition & Drift — {fund_name}</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Top KPI Strip (Typography-driven)
    num_holdings = conc.get('Number of Holdings')
    active_pos = str(num_holdings) if num_holdings is not None else str(len(holdings))

    p1_top5 = conc.get('Top 5 Holdings Weight')
    top5_str = f"{p1_top5:.2%}" if pd.notna(p1_top5) else "—"
    p1_hhi = conc.get('HHI')
    hhi_str = f"{p1_hhi:.4f}" if pd.notna(p1_hhi) else "—"
    p1_eff = conc.get('Effective Number of Holdings')
    eff_str = f"{p1_eff:.1f}" if pd.notna(p1_eff) else "—"

    st.markdown(
        f"""
        <div class="stat-row">
            <div class="stat-item">
                <div class="stat-item-label">Active Positions</div>
                <div class="stat-item-value">{active_pos}</div>
            </div>
            <div class="stat-item">
                <div class="stat-item-label">Top 5 Weight</div>
                <div class="stat-item-value">{top5_str}</div>
            </div>
            <div class="stat-item">
                <div class="stat-item-label">Herfindahl Index (HHI)</div>
                <div class="stat-item-value">{hhi_str}</div>
            </div>
            <div class="stat-item">
                <div class="stat-item-label">Effective Holdings</div>
                <div class="stat-item-value">{eff_str}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

    # Primary Element: Holdings Drift Table
    st.caption(f"Full Holdings Weightage & Rebalance Drift Ledger (Threshold: ±{threshold:.1f}pp)")
    rebalance_df = rebalance.compute_weight_drift(holdings, previous_holdings, threshold=threshold)
    rebalance_display = rebalance_df.copy()
    rebalance_display.index = range(1, len(rebalance_display) + 1)
    st.dataframe(
        rebalance_display.style.apply(
            lambda row: [
                "background-color: rgba(248, 81, 73, 0.12)" if row["Rebalance Required"] else ""
                for _ in row
            ],
            axis=1,
        ).format(
            {
                "Current Weight": "{:.2f}%",
                "Previous Weight": "{:.2f}%",
                "Drift": "{:+.2f} pp",
            }
        ),
        use_container_width=True,
    )

    st.markdown("<div style='height: 0.75rem;'></div>", unsafe_allow_html=True)

    # Lower Breakdown: Sector & Market Cap
    c_sec, c_mcap = st.columns(2)
    with c_sec:
        st.caption("Sector Allocation")
        sec_df = analytics.get("Sector Allocation", pd.DataFrame())
        st.dataframe(sec_df.style.format({"Weight": "{:.2%}"}), use_container_width=True, hide_index=True)

    with c_mcap:
        st.caption("Market Cap Allocation")
        mcap_df = analytics.get("Market Cap Allocation", pd.DataFrame())
        if not mcap_df.empty:
            st.dataframe(mcap_df.style.format({"Weight": "{:.2%}"}), use_container_width=True, hide_index=True)
        else:
            st.info("Market-cap breakdown not available for this snapshot.")

    if len(fund_codes) > 1:
        st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)
        st.caption("Cross-Fund Holdings Overlap")
        overlap_table = research.compare_funds_for_overlap(
            fund_data,
            [fund_code] + [f for f in fund_codes if f != fund_code],
        )
        if not overlap_table.empty:
            overlap_table["Holding Overlap Ratio"] = overlap_table["Holding Overlap Ratio"].map(
                lambda v: f"{v:.2%}" if pd.notna(v) else "—"
            )
            overlap_table["Weight Overlap"] = overlap_table["Weight Overlap"].map(
                lambda v: f"{v:.2%}" if pd.notna(v) else "—"
            )
            st.dataframe(overlap_table, use_container_width=True, hide_index=True)


# =============================================================================
# 5. RESEARCH WORKSPACE
# =============================================================================

def render_research_page(fund_data, fundamental_data: pd.DataFrame, fund_codes: list) -> None:
    """Render Cross-Fund Intelligence and Fundamental Screener."""
    st.markdown(
        """
        <div class="page-header">
            <div class="page-header-label">MULTI-FUND RESEARCH</div>
            <h1 class="page-header-title">Cross-Fund Comparison & Equity Screener</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )

    research_period = st.selectbox("Window Period", performance.PERIOD_ORDER, key="res_period_sel")
    research_df = research.build_fund_comparison(fund_data, period=research_period)

    if research_df.empty:
        st.info(f"No funds have sufficient history for period: {research_period}.")
        return

    st.dataframe(build_research_display_frame(research_df), use_container_width=True, hide_index=True)

    st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.caption("Return vs Benchmark by Fund")
        ret_data = research_df[["Fund", "Absolute Return", "Benchmark Return"]].melt(id_vars="Fund", var_name="Metric", value_name="Return")
        st.plotly_chart(dashboard_charts.build_research_returns_chart(ret_data), use_container_width=True, key="research_returns")

    with c2:
        st.caption("Active Return Generation by Fund")
        act_data = research_df[["Fund", "Active Return"]].copy()
        st.plotly_chart(dashboard_charts.build_active_return_chart(act_data), use_container_width=True, key="research_active_return")

    st.markdown("---")
    st.markdown('<div class="section-title" style="font-size: 1.15rem; margin-bottom: 0.5rem;">Fundamental Equity Screener</div>', unsafe_allow_html=True)
    selected_fund = st.selectbox("Select Fund Holdings to Screen", fund_codes, key="fund_screener_sel")
    weightage_fund = fund_data.weightage[fund_data.weightage["Fund Code"] == selected_fund]
    st.dataframe(
        build_fundamental_display_frame(weightage_fund, fund_data.mapping, fundamental_data),
        use_container_width=True,
        hide_index=True,
    )


# =============================================================================
# 6. ATTRIBUTION WORKSPACE
# =============================================================================

@st.cache_data(show_spinner="Fetching monthly attribution from Yahoo Finance...")
def _load_historical_attribution_cached(
    _weightage, _mapping, _sector_data, fund_code
):
    fund_weightage = _weightage[_weightage["Fund Code"] == fund_code].copy()
    if _sector_data is not None and not _sector_data.empty:
        sector_cols = [c for c in ["ISIN", "Sector"] if c in _sector_data.columns]
        if len(sector_cols) == 2:
            sec_lookup = _sector_data[sector_cols].drop_duplicates("ISIN")
            if "Sector" in fund_weightage.columns:
                fund_weightage = fund_weightage.drop(columns=["Sector"])
            fund_weightage = fund_weightage.merge(sec_lookup, on="ISIN", how="left")

    return attribution.compute_monthly_attribution(fund_weightage, _mapping, top_n=5)


def render_attribution_page(
    fund_data,
    fund_code: str,
    fund_name: str,
    snapshot_date: object,
    holdings: pd.DataFrame,
    previous_holdings: pd.DataFrame | None,
    sector_data: pd.DataFrame,
    available_dates: list,
    perf: dict,
    period_perf: dict,
    threshold: float,
) -> None:
    """Render Performance Drivers, Stock Contributors, and Report Station."""
    st.markdown(
        f"""
        <div class="page-header">
            <div class="page-header-label">ATTRIBUTION</div>
            <h1 class="page-header-title">Performance Drivers & Holdings Changes — {fund_name}</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_contrib, tab_changes, tab_export = st.tabs(["Performance Contribution", "Holdings Changes", "Report Export"])

    with tab_contrib:
        st.markdown('<div class="section-title" style="font-size: 1.15rem; margin-bottom: 0.5rem;">Historical Monthly Attribution Timeline</div>', unsafe_allow_html=True)
        if st.button("Load Historical Timeline", key="btn_load_hist_attr"):
            hist_attr = _load_historical_attribution_cached(
                fund_data.weightage, fund_data.mapping, sector_data, fund_code
            )
            st.session_state["hist_attr_result"] = (fund_code, hist_attr)

        hist_res = st.session_state.get("hist_attr_result")
        if hist_res is not None and hist_res[0] == fund_code:
            hist_data = hist_res[1]
            if not hist_data:
                st.info("At least two snapshots are required for historical attribution.")
            else:
                summary_rows = [
                    {
                        "Month": month,
                        "Total Contribution": res["total_contribution"],
                        "Window Start": res["window_start"],
                        "Window End": res["window_end"],
                    }
                    for month, res in hist_data.items()
                ]
                summary_df = pd.DataFrame(summary_rows)
                st.plotly_chart(dashboard_charts.build_monthly_contribution_chart(summary_df), use_container_width=True, key="attribution_monthly_contribution")
                st.dataframe(summary_df.style.format({"Total Contribution": "{:+.2f} pp"}), use_container_width=True, hide_index=True)

                st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)
                sel_month = st.selectbox(
                    "Inspect Specific Month",
                    list(hist_data.keys()),
                    format_func=lambda m: pd.Timestamp(m).strftime("%b %Y"),
                    key="attr_month_sel",
                )
                month_res = hist_data[sel_month]
                top5 = month_res.get("top")
                bot5 = month_res.get("bottom")
                if top5 is None or bot5 is None:
                    top5, bot5 = attribution.top_bottom_contributors(month_res["data"], n=5)

                col1, col2 = st.columns(2)
                with col1:
                    st.caption("Top 5 Stock Contributors")
                    st.altair_chart(dashboard_charts.build_contributor_chart(top5, "#2EA043"), use_container_width=True)
                    st.dataframe(top5[["Stock Name", "Current Weight", "Stock Return", "Contribution"]].style.format({
                        "Current Weight": "{:.2f}%", "Stock Return": "{:+.2%}", "Contribution": "{:+.2f} pp"
                    }), use_container_width=True, hide_index=True)

                with col2:
                    st.caption("Bottom 5 Stock Contributors")
                    st.altair_chart(dashboard_charts.build_contributor_chart(bot5, "#F85149"), use_container_width=True)
                    st.dataframe(bot5[["Stock Name", "Current Weight", "Stock Return", "Contribution"]].style.format({
                        "Current Weight": "{:.2f}%", "Stock Return": "{:+.2%}", "Contribution": "{:+.2f} pp"
                    }), use_container_width=True, hide_index=True)

                sec_df = month_res.get("sector", pd.DataFrame())
                if not sec_df.empty:
                    st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)
                    st.caption(f"Sector Contribution — {pd.Timestamp(sel_month).strftime('%b %Y')}")
                    st.plotly_chart(dashboard_charts.build_sector_contribution_chart(sec_df, pd.Timestamp(sel_month).strftime('%b %Y')), use_container_width=True, key="attribution_sector_contribution")

    with tab_changes:
        st.markdown('<div class="section-title" style="font-size: 1.15rem; margin-bottom: 0.5rem;">Consecutive Snapshot Holdings Changes</div>', unsafe_allow_html=True)
        holdings_changes = rebalance.compute_holdings_changes(holdings, previous_holdings)
        st.dataframe(
            holdings_changes.style.format({
                "Previous Weight": "{:.2f}%",
                "Current Weight": "{:.2f}%",
                "Weight Change": "{:+.2f} pp",
            }),
            use_container_width=True,
            hide_index=True,
        )

    with tab_export:
        st.markdown('<div class="section-title" style="font-size: 1.15rem; margin-bottom: 0.5rem;">Institutional Excel Report Generation</div>', unsafe_allow_html=True)
        st.caption("Build complete executive workbook containing multi-period performance, stock/sector attribution, and rebalance drift.")

        if st.button("Generate Excel Report", key="btn_gen_excel_attr"):
            with st.spinner("Building fund report workbook..."):
                s = perf["summary"]
                stock_returns = attribution.fetch_stock_returns(holdings, start=s["Start Date"], end=s["End Date"])
                holdings_with_ret = holdings.merge(stock_returns, on="ISIN", how="left")
                stock_contrib = attribution.stock_contribution(holdings_with_ret)
                sector_contrib = attribution.sector_contribution(stock_contrib)
                rebal_df = rebalance.compute_weight_drift(holdings, previous_holdings, threshold=threshold)

                out_path = report_generator.build_fund_report(
                    fund_code=fund_code,
                    fund_name=fund_name,
                    perf=perf,
                    period_perf=period_perf,
                    holdings_enriched=holdings,
                    stock_contrib=stock_contrib,
                    sector_contrib=sector_contrib,
                    rebalance_df=rebal_df,
                    threshold=threshold,
                )

            with open(out_path, "rb") as f:
                st.download_button(
                    label=f"⬇ Download {out_path.name}",
                    data=f,
                    file_name=out_path.name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            st.success(f"Workbook generated: {out_path.name}")
