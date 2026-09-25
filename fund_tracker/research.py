"""
research.py
-----------
Research-oriented analytics built on top of the existing
fund performance calculation engine.
"""

import numpy as np
import pandas as pd

import config
import data_loader
import performance


def _normalise_weights(weights: pd.Series) -> pd.Series:
    """Convert holding weights to a fraction share of the portfolio.

    The project's Weightage files store percentages such as 25.0 for 25%,
    while some internal analyses pass already-normalised fractions such as
    0.25. We accept both forms and standardise to fractions in the 0..1
    range. If the total does not sum to 1 exactly, the portfolio metrics are
    computed on the normalised weight share rather than forcing a silent
    100% rescaling.
    """
    values = pd.to_numeric(weights, errors="coerce").dropna()
    if values.empty:
        return pd.Series(dtype=float)

    if (values.abs() > 1).any():
        values = values / 100.0

    values = values.astype(float)
    total = values.sum()
    if total <= 0:
        return pd.Series(dtype=float)
    return values / total


def _clean_snapshot(holdings: pd.DataFrame | None) -> pd.DataFrame:
    """Drop cash and invalid rows, aggregate duplicate ISIN rows for a single snapshot."""
    if holdings is None or holdings.empty:
        return pd.DataFrame(columns=["ISIN", "Current Weight"])

    df = holdings.copy()
    if "Current Weight" not in df.columns:
        return pd.DataFrame(columns=["ISIN", "Current Weight"])

    df["Current Weight"] = pd.to_numeric(df["Current Weight"], errors="coerce")
    if "Is Cash" in df.columns:
        df = df[~df["Is Cash"].fillna(False)].copy()
    df = df.dropna(subset=["Current Weight"]).copy()
    if df.empty:
        return pd.DataFrame(columns=["ISIN", "Current Weight"])

    if "ISIN" in df.columns:
        df = df.groupby("ISIN", as_index=False)["Current Weight"].sum()

    return df


def top_holding_weight(holdings: pd.DataFrame, top_n: int = 5) -> float:
    """Share of the portfolio held in the top N positions, as a fraction."""
    clean = _clean_snapshot(holdings)
    if clean.empty:
        return np.nan

    weights = _normalise_weights(clean["Current Weight"])
    if weights.empty:
        return np.nan

    return float(weights.sort_values(ascending=False).head(top_n).sum())


def top_5_holding_weight(holdings: pd.DataFrame) -> float:
    return top_holding_weight(holdings, top_n=5)


def top_10_holding_weight(holdings: pd.DataFrame) -> float:
    return top_holding_weight(holdings, top_n=10)


def number_of_holdings(holdings: pd.DataFrame) -> int:
    """Count of real, non-cash holdings in the snapshot."""
    clean = _clean_snapshot(holdings)
    return int(len(clean)) if not clean.empty else 0


def hhi(holdings: pd.DataFrame) -> float:
    """Herfindahl-Hirschman Index using portfolio weights as fractions.

    Convention: weights are normalized to share-of-portfolio fractions, then
    HHI = sum(weight_i^2). This intentionally does not multiply by 10,000.
    """
    clean = _clean_snapshot(holdings)
    if clean.empty:
        return np.nan

    weights = _normalise_weights(clean["Current Weight"])
    if weights.empty:
        return np.nan
    return float(np.sum(weights ** 2))


def effective_number_of_holdings(holdings: pd.DataFrame) -> float:
    """Diversification metric = 1 / HHI, with HHI computed on weights as fractions."""
    h = hhi(holdings)
    if pd.isna(h) or h <= 0:
        return np.nan
    return float(1.0 / h)


def sector_allocation(holdings: pd.DataFrame) -> pd.DataFrame:
    """Aggregate portfolio weight by sector; return a DataFrame with Sector and Weight."""
    if holdings is None or holdings.empty:
        return pd.DataFrame(columns=["Sector", "Weight"])

    df = holdings.copy()
    if "Current Weight" not in df.columns:
        return pd.DataFrame(columns=["Sector", "Weight"])

    df["Current Weight"] = pd.to_numeric(df["Current Weight"], errors="coerce")
    if "Is Cash" in df.columns:
        df = df[~df["Is Cash"].fillna(False)].copy()
    df = df.dropna(subset=["Current Weight"]).copy()
    if df.empty:
        return pd.DataFrame(columns=["Sector", "Weight"])

    df["Sector"] = df.get("Sector", pd.Series(["Unknown"] * len(df), index=df.index))
    df["Sector"] = df["Sector"].replace({None: "Unknown", "": "Unknown", np.nan: "Unknown"})
    df["Sector"] = df["Sector"].astype(str).str.strip()
    df.loc[df["Sector"] == "", "Sector"] = "Unknown"
    df.loc[df["Sector"] == "nan", "Sector"] = "Unknown"

    weights = _normalise_weights(df["Current Weight"])
    if weights.empty:
        return pd.DataFrame(columns=["Sector", "Weight"])

    sector_df = pd.DataFrame({"Sector": df["Sector"].values, "Weight": weights.values})
    sector_df = sector_df.groupby("Sector", as_index=False)["Weight"].sum()
    sector_df = sector_df.sort_values("Weight", ascending=False).reset_index(drop=True)
    sector_df["Weight"] = sector_df["Weight"].astype(float)
    return sector_df


def classify_market_cap(value: float | int | str, large_cap_threshold: float = None, mid_cap_threshold: float = None) -> str:
    """Classify a market-cap value using configurable thresholds.

    Defaults are documented in config.MARKET_CAP_THRESHOLDS and may be
    overridden for analysis, but the function never invents a cap bucket when
    the value itself is missing or unusable.
    """
    if large_cap_threshold is None or mid_cap_threshold is None:
        large_cap_threshold = config.MARKET_CAP_LARGE_CAP_THRESHOLD
        mid_cap_threshold = config.MARKET_CAP_MID_CAP_THRESHOLD

    try:
        cap = float(value)
    except (TypeError, ValueError):
        return "Unknown"

    if pd.isna(cap) or cap <= 0:
        return "Unknown"
    if cap >= large_cap_threshold:
        return "Large Cap"
    if cap >= mid_cap_threshold:
        return "Mid Cap"
    return "Small Cap"


def market_cap_allocation(holdings: pd.DataFrame, market_cap_data: pd.DataFrame | None = None) -> pd.DataFrame:
    """Aggregate portfolio weight by market-cap classification. Missing values remain Unknown."""
    if holdings is None or holdings.empty:
        return pd.DataFrame(columns=["Market Cap Bucket", "Weight"])

    df = holdings.copy()
    if "Current Weight" not in df.columns:
        return pd.DataFrame(columns=["Market Cap Bucket", "Weight"])

    df["Current Weight"] = pd.to_numeric(df["Current Weight"], errors="coerce")
    if "Is Cash" in df.columns:
        df = df[~df["Is Cash"].fillna(False)].copy()
    df = df.dropna(subset=["Current Weight"]).copy()
    if df.empty:
        return pd.DataFrame(columns=["Market Cap Bucket", "Weight"])

    if market_cap_data is not None and not market_cap_data.empty:
        lookup = market_cap_data[["ISIN", "Market Cap"]].drop_duplicates(subset=["ISIN"])
        df = df.merge(lookup, on="ISIN", how="left")
    elif "Market Cap" not in df.columns:
        df["Market Cap"] = np.nan

    weights = _normalise_weights(df["Current Weight"])
    if weights.empty:
        return pd.DataFrame(columns=["Market Cap Bucket", "Weight"])

    df["Market Cap Bucket"] = df["Market Cap"].apply(classify_market_cap)
    allocation = pd.DataFrame({"Market Cap Bucket": df["Market Cap Bucket"].values, "Weight": weights.values})
    allocation = allocation.groupby("Market Cap Bucket", as_index=False)["Weight"].sum()
    allocation = allocation.sort_values("Weight", ascending=False).reset_index(drop=True)
    return allocation


def compute_holdings_overlap(fund_a: pd.DataFrame, fund_b: pd.DataFrame) -> dict:
    """Compare two holdings snapshots by common holdings count and weight overlap.

    Weight overlap is computed as sum(min(weight_a_i, weight_b_i)) over the
    common holdings, using each fund's portfolio weights normalised to a
    share-of-portfolio fraction. This is symmetric by construction.
    """
    a = _clean_snapshot(fund_a)
    b = _clean_snapshot(fund_b)
    if a.empty or b.empty:
        return {
            "Common Holdings": 0,
            "Holding Overlap Ratio": 0.0,
            "Weight Overlap": 0.0,
            "Common Holdings List": [],
        }

    a_map = a.set_index("ISIN")["Current Weight"]
    b_map = b.set_index("ISIN")["Current Weight"]

    # Normalize against each complete portfolio before restricting the
    # comparison to common holdings. Otherwise each fund's common subset is
    # incorrectly treated as a 100% portfolio.
    a_norm = _normalise_weights(a_map)
    b_norm = _normalise_weights(b_map)

    common = sorted(set(a_map.index) & set(b_map.index))
    if not common:
        return {
            "Common Holdings": 0,
            "Holding Overlap Ratio": 0.0,
            "Weight Overlap": 0.0,
            "Common Holdings List": [],
        }

    common_a = a_norm.reindex(common, fill_value=0.0)
    common_b = b_norm.reindex(common, fill_value=0.0)
    weight_overlap = float(np.minimum(common_a.to_numpy(), common_b.to_numpy()).sum())

    union = sorted(set(a_map.index) | set(b_map.index))
    overlap_ratio = float(len(common) / len(union)) if union else 0.0

    return {
        "Common Holdings": len(common),
        "Holding Overlap Ratio": overlap_ratio,
        "Weight Overlap": weight_overlap,
        "Common Holdings List": common,
    }


def compute_portfolio_change(current_holdings: pd.DataFrame, previous_holdings: pd.DataFrame | None = None) -> dict:
    """Compute a simple portfolio-change summary between two snapshots.

    The available data supports weight drift rather than a formal fund-turnover
    figure. Formula used here for turnover-like comparison is:
        turnover = 0.5 * sum(abs(w_t - w_t-1))
    across all holdings in the union of the two snapshots.
    """
    current = _clean_snapshot(current_holdings)
    previous = _clean_snapshot(previous_holdings)

    if current.empty:
        return {
            "Total Absolute Weight Change": np.nan,
            "Additions": np.nan,
            "Removals": np.nan,
            "Turnover": np.nan,
            "Largest Weight Increases": pd.DataFrame(columns=["ISIN", "Weight Change"]),
            "Largest Weight Decreases": pd.DataFrame(columns=["ISIN", "Weight Change"]),
        }

    current_map = current.set_index("ISIN")["Current Weight"]
    prev_map = previous.set_index("ISIN")["Current Weight"] if not previous.empty else pd.Series(dtype=float)

    all_isins = sorted(set(current_map.index) | set(prev_map.index))
    current_norm = _normalise_weights(current_map.reindex(all_isins).fillna(0.0))
    previous_norm = _normalise_weights(prev_map.reindex(all_isins).fillna(0.0))
    delta = current_norm - previous_norm

    total_abs_change = float(delta.abs().sum())
    additions = float((delta.clip(lower=0)).sum())
    removals = float((-delta.clip(upper=0)).sum())
    turnover = 0.5 * total_abs_change

    increases = pd.DataFrame({
        "ISIN": delta[delta > 0].index,
        "Weight Change": delta[delta > 0].values,
    }).sort_values("Weight Change", ascending=False).reset_index(drop=True)
    decreases = pd.DataFrame({
        "ISIN": delta[delta < 0].index,
        "Weight Change": delta[delta < 0].values,
    }).sort_values("Weight Change", ascending=True).reset_index(drop=True)

    return {
        "Total Absolute Weight Change": total_abs_change,
        "Additions": additions,
        "Removals": removals,
        "Turnover": turnover,
        "Largest Weight Increases": increases.head(5),
        "Largest Weight Decreases": decreases.head(5),
    }


def build_portfolio_analytics(fund_data: object, fund_code: str, as_of: str | None = None, fundamental_data: pd.DataFrame | None = None) -> dict:
    """Build a reusable portfolio-analytics summary for one fund snapshot."""
    if fund_data is None or fund_data.weightage.empty:
        return {"Available": False, "Reason": "No fund data available."}

    snapshot = data_loader.latest_snapshot(fund_data.weightage, fund_code, as_of=as_of)
    if snapshot.empty:
        return {"Available": False, "Reason": f"No Weightage snapshot found for {fund_code}."}

    concentration = {
        "Top 5 Holdings Weight": top_5_holding_weight(snapshot),
        "Top 10 Holdings Weight": top_10_holding_weight(snapshot),
        "Number of Holdings": number_of_holdings(snapshot),
        "HHI": hhi(snapshot),
        "Effective Number of Holdings": effective_number_of_holdings(snapshot),
    }

    sector_df = sector_allocation(snapshot)
    sector_df.rename(columns={"Weight": "Weight"}, inplace=True)

    market_cap_df = pd.DataFrame(columns=["Market Cap Bucket", "Weight"])
    if fundamental_data is not None and not fundamental_data.empty:
        market_cap_df = market_cap_allocation(snapshot, fundamental_data)

    return {
        "Available": True,
        "Snapshot Date": snapshot["Date"].max(),
        "Snapshot": snapshot,
        "Top Holdings": snapshot.sort_values("Current Weight", ascending=False).head(10).copy(),
        "Concentration": concentration,
        "Sector Allocation": sector_df,
        "Market Cap Allocation": market_cap_df,
        "Diversification": {
            "HHI": concentration["HHI"],
            "Effective Number of Holdings": concentration["Effective Number of Holdings"],
            "Top 5 Holdings Weight": concentration["Top 5 Holdings Weight"],
            "Top 10 Holdings Weight": concentration["Top 10 Holdings Weight"],
        },
    }


def compare_funds_for_overlap(fund_data: object, fund_codes: list[str]) -> pd.DataFrame:
    """Compare funds using each pair's latest common holdings snapshot date.

    Rows with no common snapshot date are returned as unavailable rather than
    comparing independently latest snapshots.
    """
    columns = [
        "Fund",
        "Snapshot Date",
        "Available",
        "Reason",
        "Common Holdings",
        "Holding Overlap Ratio",
        "Weight Overlap",
    ]
    if not fund_codes:
        return pd.DataFrame(columns=columns)

    baseline = fund_codes[0]
    rows = []
    for fund_code in fund_codes[1:]:
        baseline_rows = fund_data.weightage[
            fund_data.weightage["Fund Code"] == baseline
        ]
        comparison_rows = fund_data.weightage[
            fund_data.weightage["Fund Code"] == fund_code
        ]
        common_dates = sorted(
            set(baseline_rows["Date"].unique())
            & set(comparison_rows["Date"].unique())
        )

        if not common_dates:
            rows.append({
                "Fund": fund_code,
                "Snapshot Date": pd.NaT,
                "Available": False,
                "Reason": f"No common snapshot date for {baseline} and {fund_code}.",
                "Common Holdings": np.nan,
                "Holding Overlap Ratio": np.nan,
                "Weight Overlap": np.nan,
            })
            continue

        common_date = common_dates[-1]
        base_snapshot = data_loader.latest_snapshot(
            fund_data.weightage,
            baseline,
            as_of=common_date,
        )
        other_snapshot = data_loader.latest_snapshot(
            fund_data.weightage,
            fund_code,
            as_of=common_date,
        )
        overlap = compute_holdings_overlap(base_snapshot, other_snapshot)
        rows.append({
            "Fund": fund_code,
            "Snapshot Date": common_date,
            "Available": True,
            "Reason": "",
            "Common Holdings": overlap["Common Holdings"],
            "Holding Overlap Ratio": overlap["Holding Overlap Ratio"],
            "Weight Overlap": overlap["Weight Overlap"],
        })
    return pd.DataFrame(rows, columns=columns)


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
        volatility = result.get("Volatility", np.nan)
        benchmark_vol = result.get("Benchmark Volatility", np.nan)
        sharpe = result.get("Sharpe Ratio", np.nan)
        sortino = result.get("Sortino Ratio", np.nan)
        down_dev = result.get("Downside Deviation", np.nan)
        beta = result.get("Beta", np.nan)
        jensens_alpha = result.get("Jensen's Alpha", np.nan)

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
                "Volatility": volatility,
                "Benchmark Volatility": benchmark_vol,
                "Downside Deviation": down_dev,
                "Sharpe Ratio": sharpe,
                "Sortino Ratio": sortino,
                "Beta": beta,
                "Jensen's Alpha": jensens_alpha,
            }
        )

    return pd.DataFrame(rows)