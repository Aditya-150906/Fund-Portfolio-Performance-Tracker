"""
performance.py
--------------
Pure calculation engine over a single fund's Daily NAV series:
    - Daily return
    - Cumulative return
    - Absolute return
    - CAGR
    - Benchmark comparison (active return, alpha, tracking error, information ratio)
    - Drawdown (rolling peak, current drawdown, maximum drawdown)

Every function takes/returns pandas objects and has no side effects, so it
can be unit tested in isolation from the Excel I/O.
"""

import numpy as np
import pandas as pd

import config

# Below this many years of actual data, a "CAGR" is not a meaningful
# annualised figure - it's compounding a short-window return as though it
# repeated for a full year, which blows up (or shrinks) numbers wildly.
# Example: a genuine +10% over 3 months (years=0.25) annualises to
# (1.10)^4 - 1 ~= 46%, even though nothing unusual happened. This mainly
# bites the "Current FY (Apr-Mar)" window early in the financial year, and
# "Since Inception" for a fund less than a year old. Below this threshold,
# cagr() returns NaN and callers should show the plain (non-annualised)
# Absolute Return instead - see compute_fund_performance()'s
# "CAGR Annualised" flag.
MIN_YEARS_FOR_CAGR = 1.0


def add_daily_returns(nav_df: pd.DataFrame) -> pd.DataFrame:
    """
    Daily Return = (Today's NAV / Yesterday's NAV) - 1

    Expects a single-fund frame sorted by Date, with 'Portfolio NAV' and
    'Benchmark NAV' columns. Adds 'Portfolio Return' and 'Benchmark Return'.
    """
    df = nav_df.sort_values("Date").reset_index(drop=True).copy()
    df["Portfolio Return"] = df["Portfolio NAV"].pct_change()
    df["Benchmark Return"] = df["Benchmark NAV"].pct_change()
    return df


def cumulative_return(nav_series: pd.Series) -> pd.Series:
    """Cumulative return path from the first observation to each date."""
    base = nav_series.iloc[0]
    return nav_series / base - 1


def absolute_return(nav_series: pd.Series) -> float:
    """Absolute Return = (Ending NAV / Beginning NAV) - 1, over the whole window."""
    return float(nav_series.iloc[-1] / nav_series.iloc[0] - 1)


def cagr(nav_series: pd.Series, dates: pd.Series, min_years: float = MIN_YEARS_FOR_CAGR) -> float:
    """
    CAGR = (Ending NAV / Beginning NAV) ^ (1 / years) - 1
    'years' is measured from the actual calendar span of the data, not a
    day-count assumption, so short or gappy series are still handled correctly.

    Returns NaN if the window spans less than `min_years` of real time
    (default 1 year). Annualising a short window (e.g. a 3-month "Current
    FY" slice, or a fund that's only been live a few months) doesn't
    produce a meaningful "if this rate continued for a year" number - it
    massively amplifies whatever the short-window return happened to be.
    Use absolute_return() for anything shorter than a year instead; see
    compute_fund_performance()'s "CAGR Annualised" flag for how the two are
    surfaced together.
    """
    years = (dates.iloc[-1] - dates.iloc[0]).days / 365.25
    if years <= 0:
        return np.nan
    if years < min_years:
        return np.nan
    total_growth = nav_series.iloc[-1] / nav_series.iloc[0]
    return float(total_growth ** (1 / years) - 1)


def benchmark_comparison(df: pd.DataFrame) -> dict:
    """
    Compare portfolio vs benchmark over the full window.
    df must already have 'Portfolio Return' and 'Benchmark Return' (daily).

    Active Return       = Portfolio Absolute Return - Benchmark Absolute Return
    Alpha (simplified)  = the benchmark-relative excess return over the
                          configured annualised risk-free rate, using the
                          portfolio's and benchmark's annualised CAGR values.
                          This is deliberately not the same as Jensen's alpha,
                          which is defined below and uses portfolio beta.

    Beta                = covariance(portfolio return, benchmark return) /
                          variance(benchmark return) using the aligned daily
                          return series.
    Jensen's Alpha      = Portfolio Annualised Return - [Risk Free Rate +
                          Beta * (Benchmark Annualised Return - Risk Free Rate)]
    Tracking Error       = annualised std dev of (Portfolio Return - Benchmark Return)
    Information Ratio    = annualised Active Return / Tracking Error
    """
    port_abs = absolute_return(df["Portfolio NAV"])
    bench_abs = absolute_return(df["Benchmark NAV"])
    active_return = port_abs - bench_abs

    port_cagr = cagr(df["Portfolio NAV"], df["Date"])
    bench_cagr = cagr(df["Benchmark NAV"], df["Date"])
    port_annualised_return = annualised_return(df["Portfolio Return"])
    bench_annualised_return = annualised_return(df["Benchmark Return"])
    beta = calculate_beta(df["Portfolio Return"], df["Benchmark Return"])
    alpha = (
        (port_cagr - bench_cagr - config.RISK_FREE_RATE)
        if not (np.isnan(port_cagr) or np.isnan(bench_cagr))
        else np.nan
    )
    jensen_alpha = jensens_alpha(
        port_annualised_return,
        bench_annualised_return,
        beta,
        config.RISK_FREE_RATE,
    )

    daily_diff = (df["Portfolio Return"] - df["Benchmark Return"]).dropna()
    tracking_error = float(daily_diff.std(ddof=1) * np.sqrt(config.TRADING_DAYS_PER_YEAR))

    information_ratio = (
        float(alpha / tracking_error)
        if not np.isnan(alpha) and tracking_error not in (0, np.nan)
        else np.nan
    )

    return {
        "Benchmark Return": bench_abs,
        "Active Return": active_return,
        "Alpha": alpha,
        "Beta": beta,
        "Jensen's Alpha": jensen_alpha,
        "Tracking Error": tracking_error,
        "Information Ratio": information_ratio,
    }


def drawdown_series(nav_series: pd.Series) -> pd.DataFrame:
    """
    Rolling Peak NAV -> Current NAV / Peak NAV -> Drawdown at every date.
    Returns a DataFrame with 'Rolling Peak' and 'Drawdown' (negative or zero).
    """
    rolling_peak = nav_series.cummax()
    drawdown = nav_series / rolling_peak - 1
    return pd.DataFrame({"Rolling Peak": rolling_peak, "Drawdown": drawdown})


def max_drawdown(nav_series: pd.Series) -> float:
    return float(drawdown_series(nav_series)["Drawdown"].min())


def annualised_return(daily_returns: pd.Series, trading_days=config.TRADING_DAYS_PER_YEAR) -> float:
    """
    Annualised arithmetic return from daily returns using the project's
    252-trading-day convention.

    Formula:
        annualised_return = mean(daily_returns) * trading_days

    This intentionally uses the arithmetic mean daily return rather than a
    compounded path return so the risk metrics remain usable even when CAGR is
    NaN because the history is shorter than MIN_YEARS_FOR_CAGR.
    """
    if daily_returns is None:
        return np.nan

    clean = pd.to_numeric(daily_returns, errors="coerce").dropna()
    if len(clean) < 2:
        return np.nan

    mean_daily = clean.mean()
    if pd.isna(mean_daily) or not np.isfinite(mean_daily):
        return np.nan

    return float(mean_daily * trading_days)


def annualised_volatility(daily_returns: pd.Series, trading_days=config.TRADING_DAYS_PER_YEAR) -> float:
    """
    Annualised volatility from daily returns.

    Convention: daily returns are scaled to an annual figure by multiplying the
    sample standard deviation by sqrt(TRADING_DAYS_PER_YEAR). This matches the
    standard annualisation used elsewhere in the project for risk metrics.
    """
    if len(daily_returns.dropna()) < 2:
        return np.nan
    return float(daily_returns.std(ddof=1) * np.sqrt(trading_days))

def downside_deviation(daily_returns: pd.Series, risk_free_rate=0.0, trading_days=config.TRADING_DAYS_PER_YEAR) -> float:
    """
    Annualised downside deviation.
    Risk free rate provided should be annualised. We convert it to daily.
    """
    if len(daily_returns.dropna()) < 2:
        return np.nan
    risk_free_daily = (1 + risk_free_rate) ** (1 / trading_days) - 1
    downside = daily_returns - risk_free_daily
    downside = downside[downside < 0]
    if len(downside) < 2:
        return 0.0
    # Downside deviation uses the sum of squares divided by total number of observations,
    # but since it's a sample, some use N-1 of total. Standard practice: sqrt(mean(min(R - MAR, 0)^2))
    return float(np.sqrt((downside**2).sum() / len(daily_returns.dropna())) * np.sqrt(trading_days))

def sharpe_ratio(annualised_return: float, annualised_vol: float, risk_free_rate: float) -> float:
    """
    Sharpe ratio = (annualised_return - risk_free_rate) / annualised_volatility.

    The annualised return is computed from the daily-return history using the
    project convention mean(daily_return) * 252, while volatility is the
    annualised sample standard deviation * sqrt(252). This is intentionally
    kept separate from the CAGR minimum-history rule.
    """
    if np.isclose(annualised_vol, 0.0) or np.isnan(annualised_vol):
        return np.nan
    return float((annualised_return - risk_free_rate) / annualised_vol)

def sortino_ratio(annualised_return: float, down_dev: float, risk_free_rate: float) -> float:
    """
    Sortino ratio = (annualised_return - risk_free_rate) / downside_deviation.

    As with Sharpe, the numerator uses the project annualised arithmetic return
    from available daily returns, rather than a CAGR that may be NaN for a short
    history. The denominator is annualised downside deviation computed over the
    same daily-return history.
    """
    if np.isclose(down_dev, 0.0) or np.isnan(down_dev):
        return np.nan
    return float((annualised_return - risk_free_rate) / down_dev)

def calculate_beta(port_returns: pd.Series, bench_returns: pd.Series) -> float:
    # Ensure aligned non-nan
    df = pd.concat([port_returns, bench_returns], axis=1).dropna()
    if len(df) < 2:
        return np.nan
    cov_matrix = np.cov(df.iloc[:, 0], df.iloc[:, 1])
    if cov_matrix[1, 1] == 0:
        return np.nan
    return float(cov_matrix[0, 1] / cov_matrix[1, 1])

def jensens_alpha(annualised_return: float, bench_annualised_return: float, beta: float, risk_free_rate: float) -> float:
    """
    Jensen's alpha is defined as:
        alpha = R_p - [R_f + beta * (R_b - R_f)]

    where:
      - R_p is the portfolio's annualised return,
      - R_f is the annualised risk-free rate,
      - beta is portfolio beta relative to the benchmark,
      - R_b is the benchmark's annualised return.

    This is distinct from the simplified relative-alpha used in
    benchmark_comparison() and must be calculated explicitly from beta.
    The numerator uses the annualised arithmetic return from daily returns,
    not the historical CAGR, so short windows remain usable for risk analytics.
    """
    if np.isnan(beta) or np.isnan(annualised_return) or np.isnan(bench_annualised_return):
        return np.nan
    expected_return = risk_free_rate + beta * (bench_annualised_return - risk_free_rate)
    return float(annualised_return - expected_return)

def rolling_volatility(daily_returns: pd.Series, window=126, trading_days=config.TRADING_DAYS_PER_YEAR) -> pd.Series:
    """Rolling annualised volatility. Default window = 126 days (~6 months)."""
    return daily_returns.rolling(window).std(ddof=1) * np.sqrt(trading_days)

def rolling_sharpe(daily_returns: pd.Series, risk_free_rate=0.0, window=126, trading_days=config.TRADING_DAYS_PER_YEAR) -> pd.Series:
    """
    Rolling Sharpe ratio. Default window = 126 days.

    Formula used here:
        rolling Sharpe = (rolling mean daily return * 252 - risk_free_rate) /
                          annualised rolling volatility

    The numerator is the annualised arithmetic mean daily return over the rolling
    window, not a compounded return. This matches the project's 252-day annualisation
    convention and keeps the metric comparable to the standard period-based Sharpe
    ratio calculated from daily returns.
    """
    roll_mean = daily_returns.rolling(window).mean() * trading_days
    roll_vol = rolling_volatility(daily_returns, window, trading_days)
    roll_vol = roll_vol.replace(0.0, np.nan)
    return (roll_mean - risk_free_rate) / roll_vol


def compute_fund_performance(nav_df_single_fund: pd.DataFrame) -> dict:
    """
    Full performance summary for one fund's NAV history.
    Returns a dict of scalar metrics plus the enriched daily DataFrame,
    ready to be dropped straight into the report generator.
    """
    df = add_daily_returns(nav_df_single_fund)
    df["Cumulative Portfolio Return"] = cumulative_return(df["Portfolio NAV"])
    df["Cumulative Benchmark Return"] = cumulative_return(df["Benchmark NAV"])

    dd = drawdown_series(df["Portfolio NAV"])
    df["Rolling Peak NAV"] = dd["Rolling Peak"]
    df["Drawdown"] = dd["Drawdown"]

    bench = benchmark_comparison(df)

    window_years = (df["Date"].iloc[-1] - df["Date"].iloc[0]).days / 365.25

    rf = config.RISK_FREE_RATE
    cagr_port = cagr(df["Portfolio NAV"], df["Date"])
    cagr_bench = cagr(df["Benchmark NAV"], df["Date"])
    annualised_port_return = annualised_return(df["Portfolio Return"])
    annualised_bench_return = annualised_return(df["Benchmark Return"])

    vol_port = annualised_volatility(df["Portfolio Return"])
    vol_bench = annualised_volatility(df["Benchmark Return"])
    down_dev = downside_deviation(df["Portfolio Return"], risk_free_rate=rf)

    sharpe = sharpe_ratio(annualised_port_return, vol_port, rf)
    sortino = sortino_ratio(annualised_port_return, down_dev, rf)
    beta = calculate_beta(df["Portfolio Return"], df["Benchmark Return"])
    j_alpha = jensens_alpha(annualised_port_return, annualised_bench_return, beta, rf)

    df["Rolling Volatility"] = rolling_volatility(df["Portfolio Return"])
    df["Rolling Sharpe"] = rolling_sharpe(df["Portfolio Return"], risk_free_rate=rf)

    summary = {
        "Start Date": df["Date"].iloc[0],
        "End Date": df["Date"].iloc[-1],
        "Portfolio NAV (Start)": float(df["Portfolio NAV"].iloc[0]),
        "Portfolio NAV (End)": float(df["Portfolio NAV"].iloc[-1]),
        "Benchmark NAV (Start)": float(df["Benchmark NAV"].iloc[0]),
        "Benchmark NAV (End)": float(df["Benchmark NAV"].iloc[-1]),
        "Absolute Return": absolute_return(df["Portfolio NAV"]),
        "CAGR": cagr_port,
        "Volatility": vol_port,
        "Benchmark Volatility": vol_bench,
        "Downside Deviation": down_dev,
        "Sharpe Ratio": sharpe,
        "Sortino Ratio": sortino,
        "Beta": beta,
        "Jensen's Alpha": j_alpha,
        # False whenever the window is under MIN_YEARS_FOR_CAGR (~1 year):
        # in that case "CAGR" above is NaN by design (see cagr()) and the
        # report should display "Absolute Return" instead of an annualised
        # figure for this period - annualising a partial year is what
        # produced misleadingly large numbers (e.g. a 3-month gain showing
        # as a ~45% "CAGR") before this flag existed.
        "CAGR Annualised": window_years >= MIN_YEARS_FOR_CAGR,
        "Maximum Drawdown": df["Drawdown"].min(),
        **bench,
    }

    return {"daily": df, "summary": summary}


# ---------------------------------------------------------------------------
# Trailing / financial-year period windows
# ---------------------------------------------------------------------------
# "Current date" for the trailing windows below is the most recent date
# actually present in the fund's NAV series (its End Date), not today's
# calendar date - NAV data is only ever as fresh as the last row in the
# Daily NAV file, so anchoring on today's date would just shorten every
# window by however many days stale the file is. In the normal case where
# the NAV file is kept up to date, the two are the same thing.
PERIOD_ORDER = ["Since Inception", "Last 5Y", "Last 3Y", "Last 1Y", "Current FY (Apr-Mar)"]


def _financial_year_start(as_of: pd.Timestamp) -> pd.Timestamp:
    """Start of the Indian financial year (1 Apr) containing `as_of`."""
    as_of = pd.Timestamp(as_of)
    year = as_of.year if as_of.month >= 4 else as_of.year - 1
    return pd.Timestamp(year=year, month=4, day=1)


def _period_windows(as_of: pd.Timestamp) -> dict:
    """{label: start_date_or_None} for every period in PERIOD_ORDER, anchored
    on `as_of` (a fund's latest available NAV date). start=None means
    'since inception' - no lower bound."""
    return {
        "Since Inception": None,
        "Last 5Y": as_of - pd.DateOffset(years=5),
        "Last 3Y": as_of - pd.DateOffset(years=3),
        "Last 1Y": as_of - pd.DateOffset(years=1),
        "Current FY (Apr-Mar)": _financial_year_start(as_of),
    }


def compute_multi_period_performance(nav_df_single_fund: pd.DataFrame, as_of=None) -> dict:
    """
    Same metrics as compute_fund_performance() (Absolute Return, CAGR,
    Alpha, Maximum Drawdown, etc.), computed separately over each of:
    Since Inception, Last 5Y, Last 3Y, Last 1Y, and the Current Financial
    Year (1 Apr - 31 Mar), rather than only over the fund's full history.

    `as_of` optionally pins the trailing windows to a specific date
    (defaults to the latest date in the NAV series - see PERIOD_ORDER note
    above). Each holding's own NAV history sets the ceiling: if a fund is
    younger than a given window (e.g. it has only 2 years of history but
    "Last 5Y" is requested), that period is returned as unavailable rather
    than silently computed over a shorter span and mislabelled as 5Y.

    Returns {period_label: summary_dict}. Each summary_dict always has an
    "Available" key (bool); when True it has the same keys as
    compute_fund_performance()['summary'] plus "Window Start"/"Window End",
    plus a "Daily" key holding that period's own enriched daily DataFrame
    (Portfolio/Benchmark NAV, daily & cumulative return, drawdown - all
    rebased so cumulative return starts at 0% at the *period's* start date,
    not the fund's inception). This is what lets a caller plot a chart for
    "just the Last 1Y" etc. rather than only reporting the period's summary
    numbers against a since-inception chart. When "Available" is False, a
    human-readable "Reason" is given instead.

    NOTE on "Current FY (Apr-Mar)" specifically: this window is almost
    always under a year (it's however much of the financial year has
    elapsed so far). Its summary_dict['CAGR'] will therefore usually be
    NaN with summary_dict['CAGR Annualised'] = False - by design, see
    cagr()/compute_fund_performance() above. Use
    summary_dict['Absolute Return'] for this period instead of CAGR; that
    is the non-annualised, actually-meaningful number for a partial year.
    """
    full_df = nav_df_single_fund.sort_values("Date").reset_index(drop=True)
    inception = full_df["Date"].iloc[0]
    anchor = pd.Timestamp(as_of) if as_of else full_df["Date"].iloc[-1]
    full_df = full_df[full_df["Date"] <= anchor]

    windows = _period_windows(anchor)
    results = {}

    for label in PERIOD_ORDER:
        start = windows[label]
        window_df = full_df if start is None else full_df[full_df["Date"] >= start]

        if len(window_df) < 2:
            results[label] = {
                "Available": False,
                "Reason": (
                    f"No NAV data on/after {start.date()}"
                    if start is not None else "No NAV data available"
                ),
            }
            continue

        perf = compute_fund_performance(window_df)
        s = perf["summary"]
        s["Available"] = True
        # A fund younger than the requested window (e.g. 2Y of history but
        # "Last 5Y" requested) still returns a result - just flagged as
        # covering less than the full nominal window, so it isn't mistaken
        # for a true 5-year number.
        s["Truncated"] = bool(start is not None and inception > start)
        s["Window Start"] = start if start is not None else inception
        s["Window End"] = anchor
        # The period's own enriched daily frame - NAV, daily/cumulative
        # return, drawdown - all computed fresh over just this window (not
        # sliced out of the since-inception frame), so cumulative return
        # correctly starts at 0% at this period's own start date. Lets a
        # caller chart "just this period" instead of only the full history.
        s["Daily"] = perf["daily"]
        results[label] = s

    return results
