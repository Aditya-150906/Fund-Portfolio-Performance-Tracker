"""
rebalance.py
------------
No manager-entered target weight anymore - rebalancing is fully automatic.
A holding is flagged when its Current Weight has drifted from its Previous
Weight (the fund's prior month-end Weightage snapshot, same ISIN) by more
than a configurable threshold:

    Drift = Current Weight - Previous Weight
    |Drift| > Threshold  ->  "Rebalance Required"

A holding that's brand new this month (wasn't held last month) has a
Previous Weight of 0%, so a large new position is naturally flagged; a
holding that was fully exited since last month shows a Current Weight of 0%
with whatever it used to be as its Previous Weight - both cases surface
correctly without any manual input.

If there's no earlier snapshot to compare against yet (e.g. a fund's very
first month-end), every holding's Previous Weight is treated as 0% - i.e.
the entire current allocation shows up as "new", which is the correct,
non-misleading behaviour for a fund with no prior snapshot.
"""

import pandas as pd

import config


def compute_holdings_changes(
    current_holdings: pd.DataFrame,
    previous_holdings: pd.DataFrame = None,
) -> pd.DataFrame:
    """Classify consecutive snapshot changes without inferring transactions.

    Weights remain percentage values, consistent with Weightage inputs and
    ``compute_weight_drift``. New and exited describe snapshot membership;
    increased, reduced, and unchanged describe the resulting weight change.
    """
    columns = [
        "ISIN", "Stock Name", "Previous Weight", "Current Weight",
        "Weight Change", "Change Type",
    ]
    current = current_holdings.copy() if current_holdings is not None else pd.DataFrame()
    previous = previous_holdings.copy() if previous_holdings is not None else pd.DataFrame()
    required = {"ISIN", "Stock Name", "Current Weight"}
    if not required.issubset(current.columns):
        return pd.DataFrame(columns=columns)

    current = current[["ISIN", "Stock Name", "Current Weight"]].copy()
    if previous.empty or not required.issubset(previous.columns):
        previous = pd.DataFrame(columns=["ISIN", "Previous Stock Name", "Previous Weight"])
    else:
        previous = previous[["ISIN", "Stock Name", "Current Weight"]].rename(
            columns={"Current Weight": "Previous Weight", "Stock Name": "Previous Stock Name"}
        )

    merged = current.merge(previous, on="ISIN", how="outer")
    merged["Stock Name"] = merged["Stock Name"].fillna(merged["Previous Stock Name"])
    merged["Previous Weight"] = pd.to_numeric(
        merged["Previous Weight"], errors="coerce"
    ).fillna(0.0)
    merged["Current Weight"] = pd.to_numeric(
        merged["Current Weight"], errors="coerce"
    ).fillna(0.0)
    merged["Weight Change"] = merged["Current Weight"] - merged["Previous Weight"]

    current_isins = set(current["ISIN"])
    previous_isins = set(previous["ISIN"])

    def change_type(isin, weight_change):
        if isin not in previous_isins:
            return "New"
        if isin not in current_isins:
            return "Exited"
        if weight_change > 0:
            return "Increased"
        if weight_change < 0:
            return "Reduced"
        return "Unchanged"

    merged["Change Type"] = [
        change_type(isin, weight_change)
        for isin, weight_change in zip(merged["ISIN"], merged["Weight Change"])
    ]
    return merged[columns].sort_values(
        ["Change Type", "ISIN"], ascending=[True, True]
    ).reset_index(drop=True)


def compute_weight_drift(
    holdings: pd.DataFrame,
    previous_holdings: pd.DataFrame = None,
    threshold: float = config.DEFAULT_REBALANCE_THRESHOLD,
) -> pd.DataFrame:
    """
    holdings: current month's snapshot - must contain Stock Name, ISIN, Current Weight.
    previous_holdings: prior month's snapshot (same columns), or None/empty
        if this is the fund's earliest available snapshot.
    threshold: absolute drift in percentage points above which a holding is flagged.

    Returns Stock Name | ISIN | Current Weight | Previous Weight | Drift |
    Action | Rebalance Required, sorted by |Drift| descending.
    """
    current = holdings[["Stock Name", "ISIN", "Current Weight"]].copy()

    if previous_holdings is None or previous_holdings.empty:
        merged = current.copy()
        merged["Previous Weight"] = 0.0
    else:
        prev = previous_holdings[["ISIN", "Stock Name", "Current Weight"]].rename(
            columns={"Current Weight": "Previous Weight", "Stock Name": "Prev Stock Name"}
        )
        merged = current.merge(prev, on="ISIN", how="outer")
        # A holding fully exited this month has no row in `current` (Stock
        # Name/Current Weight are NaN); a brand-new holding has no row in
        # `previous_holdings` (Previous Weight is NaN). Either way, keep the
        # name that IS available and default the missing weight to 0%.
        merged["Stock Name"] = merged["Stock Name"].fillna(merged["Prev Stock Name"])
        merged = merged.drop(columns=["Prev Stock Name"])
        merged["Current Weight"] = merged["Current Weight"].fillna(0.0)
        merged["Previous Weight"] = merged["Previous Weight"].fillna(0.0)

    merged["Drift"] = merged["Current Weight"] - merged["Previous Weight"]

    def action(drift):
        if drift > threshold:
            return "Weight Increased"
        if drift < -threshold:
            return "Weight Decreased"
        return "Stable"

    merged["Action"] = merged["Drift"].apply(action)
    merged["Rebalance Required"] = merged["Drift"].abs() > threshold

    return merged[["Stock Name", "ISIN", "Current Weight", "Previous Weight", "Drift",
                   "Action", "Rebalance Required"]].sort_values(
        "Drift", key=lambda s: s.abs(), ascending=False
    ).reset_index(drop=True)
