"""
research.py
-----------
Research-oriented analytics built on top of the existing
fund performance calculation engine.
"""

import numpy as np
import pandas as pd

import performance


def build_fund_comparison(fund_data: object, period: str = "Since Inception") -> pd.DataFrame:
    """
    Build a comparable research table for every configured fund.

    Parameters
    ----------
    fund_data:
        FundData object returned by data_loader.load_all()

    period:
        One of performance.PERIOD_ORDER.

    Returns
    -------
    pd.DataFrame
        One row per fund with key research metrics.
    """

    rows = []

    fund_codes = sorted(fund_data.nav["Fund Code"].unique())

    for fund_code in fund_codes:

        fund_nav = (
            fund_data.nav[
                fund_data.nav["Fund Code"] == fund_code
            ]
            .sort_values("Date")
            .copy()
        )

        if fund_nav.empty:
            continue

        period_results = performance.compute_multi_period_performance(
            fund_nav
        )

        result = period_results.get(period)

        if result is None or not result.get("Available", False):
            continue

        # Find the fund name from the Weightage data.
        fund_rows = fund_data.weightage[
            fund_data.weightage["Fund Code"] == fund_code
        ]

        if fund_rows.empty:
            fund_name = fund_code
        else:
            fund_name = fund_rows["Fund Name"].iloc[0]

        cagr = result.get("CAGR", np.nan)
        alpha = result.get("Alpha", np.nan)
        tracking_error = result.get("Tracking Error", np.nan)
        information_ratio = result.get("Information Ratio", np.nan)

        rows.append(
            {
                "Fund": fund_name,
                "Fund Code": fund_code,
                "Absolute Return": result.get(
                    "Absolute Return", np.nan
                ),
                "CAGR": cagr,
                "Benchmark Return": result.get(
                    "Benchmark Return", np.nan
                ),
                "Active Return": result.get(
                    "Active Return", np.nan
                ),
                "Alpha": alpha,
                "Tracking Error": tracking_error,
                "Information Ratio": information_ratio,
                "Max Drawdown": result.get(
                    "Maximum Drawdown", np.nan
                ),
            }
        )

    return pd.DataFrame(rows)