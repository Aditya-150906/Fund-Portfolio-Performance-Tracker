"""
dashboard_sidebar.py
--------------------
Streamlit sidebar and file-management controls for dashboard.py.

This module owns UI orchestration only. Input validation, configuration,
security-master reloads, and cache invalidation continue to use the existing
project modules and behavior.
"""

from dataclasses import dataclass

import streamlit as st

import config
import data_loader
import security_master


@dataclass(frozen=True)
class SidebarState:
    """Values selected in the sidebar after validated fund data is loaded."""

    fund_code: str
    snapshot_date: object
    threshold: float
    available_dates: list


def render_appearance_control() -> str:
    """Render the global Light/Dark selector and return the active theme."""
    if "appearance_theme" not in st.session_state:
        st.session_state["appearance_theme"] = "Light"

    return st.sidebar.selectbox(
        "Appearance",
        ["Light", "Dark"],
        key="appearance_theme",
    )


def _render_security_master_controls() -> None:
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
            dest.write_bytes(nse_upload.getvalue())
            problems = security_master.validate_nse_master_file(dest)
            if problems:
                st.error(
                    "Couldn't use this file:\n"
                    + "\n".join(f"- {problem}" for problem in problems)
                )
            else:
                config.set_nse_security_master(dest)
                if config.has_bse_security_master():
                    security_master.reload_masters()
                st.cache_data.clear()
                st.success(f"NSE Security Master set to {nse_upload.name}.")
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
            dest.write_bytes(bse_upload.getvalue())
            problems = security_master.validate_bse_master_file(dest)
            if problems:
                st.error(
                    "Couldn't use this file:\n"
                    + "\n".join(f"- {problem}" for problem in problems)
                )
            else:
                config.set_bse_security_master(dest)
                if config.has_nse_security_master():
                    security_master.reload_masters()
                st.cache_data.clear()
                st.success(f"BSE Security Master set to {bse_upload.name}.")
                st.rerun()


def _render_configured_fund_files() -> None:
    with st.sidebar.expander(
        "Configured fund files",
        expanded=False,
    ):
        st.caption("Re-checked every run - stays configured until removed.")
        st.markdown("**Weightage file(s):**")
        if config.has_weightage_files():
            for path in config.get_weightage_files():
                st.text(f"  {path.name}")
        else:
            st.caption("  none uploaded yet")

        st.markdown("**Daily NAV file(s):**")
        if config.has_nav_files():
            for path in config.get_nav_files():
                st.text(f"  {path.name}")
        else:
            st.caption("  none uploaded yet")


def _render_add_fund_controls() -> None:
    with st.sidebar.expander(
        "Add a fund",
        expanded=not (
            config.has_weightage_files()
            and config.has_nav_files()
        ),
    ):
        st.caption("Upload a new fund's Weightage and Daily NAV Excel files.")
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
            if not new_weightage_upload or not new_nav_upload:
                st.sidebar.error(
                    "Please choose both a Weightage file and a Daily NAV file."
                )
            else:
                dest_weightage = config.INPUT_DIR / new_weightage_upload.name
                dest_nav = config.INPUT_DIR / new_nav_upload.name
                dest_weightage.write_bytes(new_weightage_upload.getvalue())
                dest_nav.write_bytes(new_nav_upload.getvalue())
                problems = (
                    data_loader.validate_weightage_file(dest_weightage)
                    + data_loader.validate_nav_file(dest_nav)
                )
                if problems:
                    st.sidebar.error(
                        "Couldn't add this fund:\n"
                        + "\n".join(f"- {problem}" for problem in problems)
                    )
                else:
                    config.add_fund_files(dest_weightage, dest_nav)
                    st.cache_data.clear()
                    st.sidebar.success(
                        f"Added {new_weightage_upload.name} / "
                        f"{new_nav_upload.name}."
                    )
                    st.rerun()


def _render_remove_fund_controls() -> None:
    with st.sidebar.expander(
        "Remove a fund",
        expanded=False,
    ):
        st.caption(
            "Un-registers a Weightage/Daily NAV file pair. "
            "The files themselves are not deleted."
        )

        if not (config.has_weightage_files() and config.has_nav_files()):
            st.caption("No fund files uploaded yet.")
            weightage_paths = []
            nav_paths = []
        else:
            weightage_paths = config.get_weightage_files()
            nav_paths = config.get_nav_files()

        if not weightage_paths and not nav_paths:
            pass
        elif len(weightage_paths) <= 1 and len(nav_paths) <= 1:
            st.caption("Only one fund file pair is configured.")
        elif len(weightage_paths) == len(nav_paths):
            for index, (weightage_path, nav_path) in enumerate(
                zip(weightage_paths, nav_paths)
            ):
                col1, col2 = st.columns([4, 1])
                col1.text(f"{weightage_path.name}\n{nav_path.name}")
                if col2.button("Remove", key=f"remove_pair_{index}"):
                    config.remove_fund_files(weightage_path, nav_path)
                    st.cache_data.clear()
                    st.sidebar.success(
                        f"Removed {weightage_path.name} / {nav_path.name}."
                    )
                    st.rerun()
        else:
            st.caption("Weightage/NAV counts do not match.")
            st.markdown("**Weightage file(s):**")
            for weightage_path in weightage_paths:
                col1, col2 = st.columns([4, 1])
                col1.text(weightage_path.name)
                if col2.button("Remove", key=f"remove_w_{weightage_path}"):
                    config.remove_weightage_file(weightage_path)
                    st.cache_data.clear()
                    st.sidebar.success(f"Removed {weightage_path.name}.")
                    st.rerun()

            st.markdown("**Daily NAV file(s):**")
            for nav_path in nav_paths:
                col1, col2 = st.columns([4, 1])
                col1.text(nav_path.name)
                if col2.button("Remove", key=f"remove_n_{nav_path}"):
                    config.remove_nav_file(nav_path)
                    st.cache_data.clear()
                    st.sidebar.success(f"Removed {nav_path.name}.")
                    st.rerun()


def render_file_management_sidebar() -> None:
    """Render security-master and configured fund-file controls."""
    st.sidebar.header("Data files")
    _render_security_master_controls()
    st.sidebar.markdown("---")
    _render_configured_fund_files()
    st.sidebar.markdown("---")
    _render_add_fund_controls()
    st.sidebar.markdown("---")
    _render_remove_fund_controls()
    st.sidebar.markdown("---")


def render_sidebar_selection(fund_data) -> SidebarState:
    """Render fund, snapshot, and rebalance settings and return their state."""
    fund_codes = data_loader.get_fund_codes(fund_data)
    fund_code = st.sidebar.selectbox("Fund", fund_codes)
    available_dates = sorted(
        fund_data.weightage.loc[
            fund_data.weightage["Fund Code"] == fund_code,
            "Date",
        ]
        .dt.date
        .unique(),
        reverse=True,
    )
    snapshot_date = st.sidebar.selectbox(
        "Weightage snapshot (month-end)",
        available_dates,
        format_func=lambda date: date.strftime("%b %Y"),
    )
    threshold = st.sidebar.slider(
        "Rebalance drift threshold (percentage points)",
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
    return SidebarState(
        fund_code=fund_code,
        snapshot_date=snapshot_date,
        threshold=threshold,
        available_dates=available_dates,
    )