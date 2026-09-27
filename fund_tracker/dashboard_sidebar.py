"""
dashboard_sidebar.py
--------------------
Streamlit sidebar control rail and file management drawers for the
Fund Research Terminal.
"""

from dataclasses import dataclass
import streamlit as st

import config
import data_loader
import security_master


@dataclass(frozen=True)
class SidebarState:
    """Values selected in the sidebar control rail."""
    fund_code: str
    snapshot_date: object
    threshold: float
    available_dates: list
    dark_mode: bool


def render_sidebar_control_panel(fund_data) -> SidebarState:
    """Render compact, restrained sidebar control rail."""
    # 1. Workspace Settings Branding
    st.sidebar.markdown(
        """
        <div style="padding-bottom: 0.75rem; margin-bottom: 0.75rem; border-bottom: 1px solid var(--border-subtle);">
            <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; font-weight: 700; letter-spacing: 0.12em; color: var(--accent); text-transform: uppercase;">
                WORKSPACE SETTINGS
            </div>
            <div style="font-size: 1.05rem; font-weight: 700; color: var(--text); letter-spacing: -0.02em;">
                Portfolio Selector
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 2. Fund & Snapshot Selectors
    fund_codes = data_loader.get_fund_codes(fund_data)
    fund_code = st.sidebar.selectbox("Active Fund", fund_codes, index=0)

    available_dates = sorted(
        fund_data.weightage.loc[
            fund_data.weightage["Fund Code"] == fund_code, "Date"
        ]
        .dt.date.unique(),
        reverse=True,
    )
    snapshot_date = st.sidebar.selectbox(
        "Snapshot Date",
        available_dates,
        format_func=lambda d: d.strftime("%d %b %Y"),
    )

    threshold = st.sidebar.slider(
        "Drift Threshold (pp)",
        min_value=1.0,
        max_value=10.0,
        value=float(config.DEFAULT_REBALANCE_THRESHOLD),
        step=0.5,
        help="Flags holdings whose weight drifted by more than this percentage points vs previous month.",
    )

    # 3. Appearance Switcher
    theme_choice = st.sidebar.radio(
        "Theme",
        ["Dark", "Light"],
        index=0,
        horizontal=True,
        key="app_theme_radio",
    )
    dark_mode = theme_choice == "Dark"

    st.sidebar.markdown("---")

    # 4. Data Management Drawers
    nse_ok = config.has_nse_security_master()
    bse_ok = config.has_bse_security_master()

    with st.sidebar.expander("Security Masters", expanded=not (nse_ok and bse_ok)):
        st.caption("Reference mapping files for ISIN to ticker resolution.")
        st.text("NSE: " + (config.get_nse_security_master().name if nse_ok else "Not Set"))
        st.text("BSE: " + (config.get_bse_security_master().name if bse_ok else "Not Set"))

        nse_file = st.file_uploader("Upload NSE Master (.csv/.xlsx)", type=["csv", "xlsx", "xls"], key="nse_up")
        if st.button("Save NSE Master", disabled=nse_file is None, key="btn_save_nse"):
            dest = config.INPUT_DIR / nse_file.name
            dest.write_bytes(nse_file.getvalue())
            probs = security_master.validate_nse_master_file(dest)
            if probs:
                st.error("Validation failed:\n" + "\n".join(f"- {p}" for p in probs))
            else:
                config.set_nse_security_master(dest)
                if config.has_bse_security_master():
                    security_master.reload_masters()
                st.cache_data.clear()
                st.success("NSE Master updated.")
                st.rerun()

        bse_file = st.file_uploader("Upload BSE Master (.csv/.xlsx)", type=["csv", "xlsx", "xls"], key="bse_up")
        if st.button("Save BSE Master", disabled=bse_file is None, key="btn_save_bse"):
            dest = config.INPUT_DIR / bse_file.name
            dest.write_bytes(bse_file.getvalue())
            probs = security_master.validate_bse_master_file(dest)
            if probs:
                st.error("Validation failed:\n" + "\n".join(f"- {p}" for p in probs))
            else:
                config.set_bse_security_master(dest)
                if config.has_nse_security_master():
                    security_master.reload_masters()
                st.cache_data.clear()
                st.success("BSE Master updated.")
                st.rerun()

    with st.sidebar.expander("Add Fund", expanded=False):
        st.caption("Upload new Weightage & Daily NAV Excel pair.")
        w_upload = st.file_uploader("Weightage File (.xlsx)", type=["xlsx", "xls"], key="new_w_up")
        n_upload = st.file_uploader("Daily NAV File (.xlsx)", type=["xlsx", "xls"], key="new_n_up")

        if st.button("Register Fund", disabled=not (w_upload and n_upload), key="btn_reg_fund"):
            dest_w = config.INPUT_DIR / w_upload.name
            dest_n = config.INPUT_DIR / n_upload.name
            dest_w.write_bytes(w_upload.getvalue())
            dest_n.write_bytes(n_upload.getvalue())
            problems = data_loader.validate_weightage_file(dest_w) + data_loader.validate_nav_file(dest_n)
            if problems:
                st.error("Validation failed:\n" + "\n".join(f"- {p}" for p in problems))
            else:
                config.add_fund_files(dest_w, dest_n)
                st.cache_data.clear()
                st.success(f"Added {w_upload.name} / {n_upload.name}")
                st.rerun()

    with st.sidebar.expander("Configured Files", expanded=False):
        if config.has_weightage_files():
            st.markdown("**Weightage Files:**")
            for p in config.get_weightage_files():
                st.text(f"• {p.name}")
        if config.has_nav_files():
            st.markdown("**Daily NAV Files:**")
            for p in config.get_nav_files():
                st.text(f"• {p.name}")

    with st.sidebar.expander("Remove Fund", expanded=False):
        w_paths = config.get_weightage_files() if config.has_weightage_files() else []
        n_paths = config.get_nav_files() if config.has_nav_files() else []
        if len(w_paths) == len(n_paths) and len(w_paths) > 0:
            for i, (w, n) in enumerate(zip(w_paths, n_paths)):
                c1, c2 = st.columns([3, 1])
                c1.caption(f"{w.name}\n{n.name}")
                if c2.button("Remove", key=f"rm_fund_{i}"):
                    config.remove_fund_files(w, n)
                    st.cache_data.clear()
                    st.success(f"Removed {w.name}")
                    st.rerun()

    return SidebarState(
        fund_code=fund_code,
        snapshot_date=snapshot_date,
        threshold=threshold,
        available_dates=available_dates,
        dark_mode=dark_mode,
    )
