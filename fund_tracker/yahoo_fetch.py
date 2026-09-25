import logging
"""
yahoo_fetch.py
--------------
Given an ISIN -> Yahoo Ticker mapping (produced by security_master.py from
the NSE/BSE Security Master files, since Yahoo Finance cannot be queried by
ISIN directly), pulls Sector / Industry from Yahoo Finance for each ticker.

Design notes
------------
* Results are cached to disk (config.SECTOR_CACHE_FILE) so re-runs on the
  same day don't re-hit the network for tickers we already resolved.
  Sector/Industry is near-static reference data, so this cache is never
  time-expired - see warm_cache.py for a way to pre-populate it entirely
  offline so live runs never touch the network for tickers already seen.
* Network calls are wrapped individually - one bad/delisted ticker will not
  crash the whole run. It is recorded as "Unknown" sector/industry instead.
* If yfinance/Yahoo Finance is unreachable (offline environment, rate limit,
  firewall) the whole module degrades gracefully to cached/"Unknown" values
  rather than raising, since sector data is an enrichment, not a hard
  dependency for the performance numbers.

Rate-limit handling
--------------------
Yahoo's unofficial API returns "Too Many Requests" (HTTP 429) if hit too
fast or too often. To stay under that limit:
  - every Yahoo Finance call goes through _throttle(), which enforces a
    minimum delay (config.YAHOO_REQUEST_DELAY) between any two calls, even
    across threads;
  - lookups for uncached tickers are parallelised across a small, bounded
    thread pool (config.YAHOO_MAX_WORKERS) rather than one ticker at a
    time or unbounded threads - a little concurrency without hammering
    Yahoo;
  - a failed call is retried with exponential backoff
    (config.YAHOO_MAX_RETRIES / config.YAHOO_BACKOFF_BASE), with extra
    backoff specifically when the failure looks like a rate limit;
  - the on-disk cache is checkpointed periodically during a run (not just
    at the end), so if a run does get rate-limited partway through,
    whatever was already fetched isn't lost and the next run picks up
    where it left off.

Speed handling
---------------
Per-ticker sector lookups are the slowest part of the pipeline (Yahoo's
assetProfile data has no true multi-ticker batch endpoint, unlike price
history). Two things help beyond raw concurrency:
  - `skip_network=True` on fetch_sector_data() answers entirely from cache
    - any ticker not already cached is marked "Unknown" immediately, with
      zero network calls. Useful for fast iteration (e.g. re-running to
      tweak target weights/thresholds) where fresh sector data isn't
      needed for that run.
  - warm_cache.py pre-populates the cache for every ISIN a fund has ever
    held, so this stays a one-time, off-hours cost rather than something
    that happens inside an interactive run.
"""

import json
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import yfinance as yf

import config
logger = logging.getLogger(__name__)

UNKNOWN = "Unknown"

# ---------------------------------------------------------------------------
# Shared rate limiter: guarantees at least config.YAHOO_REQUEST_DELAY seconds
# between any two Yahoo Finance calls, even when multiple worker threads are
# making requests concurrently.
# ---------------------------------------------------------------------------
_rate_lock = threading.Lock()
_last_call_ts = 0.0


def _throttle() -> None:
    global _last_call_ts
    with _rate_lock:
        now = time.monotonic()
        wait = config.YAHOO_REQUEST_DELAY - (now - _last_call_ts)
        if wait > 0:
            time.sleep(wait)
        _last_call_ts = time.monotonic()


def _is_rate_limit_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "429" in msg or "too many requests" in msg or "rate limit" in msg


def _load_cache() -> dict:
    if config.SECTOR_CACHE_FILE.exists():
        try:
            return json.loads(config.SECTOR_CACHE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_cache(cache: dict) -> None:
    try:
        config.SECTOR_CACHE_FILE.write_text(json.dumps(cache, indent=2))
    except OSError:
        pass  # cache is a nice-to-have, never let it break the run


def _fetch_one(ticker: str,
                retries: int = config.YAHOO_MAX_RETRIES,
                backoff: float = config.YAHOO_BACKOFF_BASE) -> dict:
    """Fetch sector/industry for a single Yahoo ticker, with throttling and
    rate-limit-aware retry/backoff."""
    for attempt in range(retries + 1):
        _throttle()
        try:
            info = yf.Ticker(ticker).get_info()
            return {
                "Sector": info.get("sector") or UNKNOWN,
                "Industry": info.get("industry") or UNKNOWN,
            }
        except Exception as exc:  # noqa: BLE001 - any network/parse failure
            rate_limited = _is_rate_limit_error(exc)
            if attempt == retries:
                reason = "rate-limited" if rate_limited else "failed"
                logger.info(f"    Could not fetch data for {ticker} ({reason}: {exc}); "
                      f"marking as {UNKNOWN}.")
                return {"Sector": UNKNOWN, "Industry": UNKNOWN}
            # Rate-limit responses get a longer backoff than ordinary
            # transient failures, plus a little jitter so multiple threads
            # don't all retry at exactly the same moment.
            wait = backoff * (attempt + 1) * (3 if rate_limited else 1) + random.uniform(0, 0.5)
            if rate_limited:
                print(f"    Rate-limited by Yahoo Finance for {ticker}; "
                      f"backing off {wait:.1f}s (attempt {attempt + 1}/{retries})...")
            time.sleep(wait)
    return {"Sector": UNKNOWN, "Industry": UNKNOWN}


def fetch_sector_data(mapping: pd.DataFrame, use_cache: bool = True,
                       skip_network: bool = False) -> pd.DataFrame:
    """
    Given the ISIN -> Yahoo Ticker mapping table, return a DataFrame:
        | ISIN | Yahoo Ticker | Sector | Industry |

    No user interaction required - this runs unattended as part of the pipeline.
    Uncached tickers are fetched via a small, bounded thread pool
    (config.YAHOO_MAX_WORKERS), with every underlying call still throttled
    and retried per _fetch_one's rate-limit handling above.

    skip_network=True answers entirely from the on-disk cache: any ticker
    not already cached is marked Unknown immediately, with no network calls
    at all. Use this for fast, iterative runs (e.g. re-running the same
    fund while tweaking target weights) where fresh sector data isn't
    needed for that particular run - see also warm_cache.py for pre-loading
    the cache so this is rarely a tradeoff in practice.
    """
    cache = _load_cache() if use_cache else {}
    rows = []
    to_fetch = []  # list of (isin, ticker) still needing a network call

    for _, row in mapping.iterrows():
        isin, ticker = row["ISIN"], row["Yahoo Ticker"]

        # Cash has no ticker to look up - Yahoo Finance would just be asked
        # for an empty string. Label it directly instead of a network call.
        if isin == "CASH" or not ticker:
            rows.append({"ISIN": isin, "Yahoo Ticker": ticker,
                         "Sector": "Cash" if isin == "CASH" else UNKNOWN,
                         "Industry": "Cash" if isin == "CASH" else UNKNOWN})
            continue

        if use_cache and ticker in cache:
            rows.append({"ISIN": isin, "Yahoo Ticker": ticker, **cache[ticker]})
        elif skip_network:
            rows.append({"ISIN": isin, "Yahoo Ticker": ticker,
                         "Sector": UNKNOWN, "Industry": UNKNOWN})
        else:
            to_fetch.append((isin, ticker))

    if to_fetch:
        logger.info(f"  Fetching sector/industry for {len(to_fetch)} ticker(s) from Yahoo "
              f"Finance (up to {config.YAHOO_MAX_WORKERS} at a time, throttled to "
              f"~{config.YAHOO_REQUEST_DELAY}s between requests to avoid rate limits)...")

        completed = 0
        with ThreadPoolExecutor(max_workers=config.YAHOO_MAX_WORKERS) as executor:
            future_to_item = {
                executor.submit(_fetch_one, ticker): (isin, ticker) for isin, ticker in to_fetch
            }
            for future in as_completed(future_to_item):
                isin, ticker = future_to_item[future]
                data = future.result()
                cache[ticker] = data
                rows.append({"ISIN": isin, "Yahoo Ticker": ticker, **data})

                # Checkpoint the cache periodically (not just at the very end)
                # so a rate-limit failure partway through a large batch
                # doesn't lose everything already fetched.
                completed += 1
                if use_cache and completed % 10 == 0:
                    _save_cache(cache)

    if use_cache:
        _save_cache(cache)

    # ThreadPoolExecutor completes out of submission order - restore the
    # original mapping order before returning.
    original_order = {isin: i for i, isin in enumerate(mapping["ISIN"])}
    rows.sort(key=lambda r: original_order.get(r["ISIN"], 0))

    return pd.DataFrame(rows)


def merge_sector_with_holdings(holdings: pd.DataFrame, sector_data: pd.DataFrame) -> pd.DataFrame:
    """Left-join sector/industry onto a holdings table by ISIN."""
    merged = holdings.merge(sector_data[["ISIN", "Sector", "Industry"]], on="ISIN", how="left")
    merged["Sector"] = merged["Sector"].fillna(UNKNOWN)
    merged["Industry"] = merged["Industry"].fillna(UNKNOWN)
    return merged
def _load_fundamental_cache() -> dict:
    cache_file = config.CACHE_DIR / "fundamental_cache.json"
    if cache_file.exists():
        try:
            return json.loads(cache_file.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}

def _save_fundamental_cache(cache: dict) -> None:
    cache_file = config.CACHE_DIR / "fundamental_cache.json"
    try:
        cache_file.write_text(json.dumps(cache, indent=2))
    except OSError:
        pass

def _fetch_fundamental_one(ticker: str, retries: int = config.YAHOO_MAX_RETRIES, backoff: float = config.YAHOO_BACKOFF_BASE) -> dict:
    for attempt in range(retries + 1):
        _throttle()
        try:
            info = yf.Ticker(ticker).get_info()
            return {
                "Market Cap": info.get("marketCap"),
                "PE Ratio": info.get("trailingPE"),
                "PB Ratio": info.get("priceToBook"),
                "ROE": info.get("returnOnEquity"),
                "Dividend Yield": info.get("dividendYield"),
                "Debt to Equity": info.get("debtToEquity"),
            }
        except Exception as exc:
            rate_limited = _is_rate_limit_error(exc)
            if attempt == retries:
                logger.info(f"    Could not fetch fundamental data for {ticker} ({'rate-limited' if rate_limited else 'failed'}: {exc})")
                return {
                    "Market Cap": None, "PE Ratio": None, "PB Ratio": None,
                    "ROE": None, "Dividend Yield": None, "Debt to Equity": None,
                }
            wait = backoff * (attempt + 1) * (3 if rate_limited else 1) + random.uniform(0, 0.5)
            time.sleep(wait)
    return {
        "Market Cap": None, "PE Ratio": None, "PB Ratio": None,
        "ROE": None, "Dividend Yield": None, "Debt to Equity": None,
    }

def fetch_fundamental_data(
    mapping: pd.DataFrame,
    use_cache: bool = True,
) -> pd.DataFrame:
    """
    Fetch basic fundamental metrics for each Yahoo Finance ticker.

    Fundamental data is cached to disk and returned as a DataFrame.

    Returns:
        ISIN
        Yahoo Ticker
        Market Cap
        PE Ratio
        PB Ratio
        ROE
        Dividend Yield
        Debt to Equity
    """
    cache = _load_fundamental_cache() if use_cache else {}
    rows = []
    to_fetch = []

    for _, row in mapping.iterrows():
        isin = row["ISIN"]
        ticker = row["Yahoo Ticker"]

        if isin == "CASH" or not ticker:
            rows.append({
                "ISIN": isin, "Yahoo Ticker": ticker,
                "Market Cap": None, "PE Ratio": None, "PB Ratio": None,
                "ROE": None, "Dividend Yield": None, "Debt to Equity": None,
            })
            continue

        if use_cache and ticker in cache:
            cached_data = cache[ticker]
            rows.append({
                "ISIN": isin, "Yahoo Ticker": ticker,
                "Market Cap": cached_data.get("Market Cap"),
                "PE Ratio": cached_data.get("PE Ratio"),
                "PB Ratio": cached_data.get("PB Ratio"),
                "ROE": cached_data.get("ROE"),
                "Dividend Yield": cached_data.get("Dividend Yield"),
                "Debt to Equity": cached_data.get("Debt to Equity"),
            })
        else:
            to_fetch.append((isin, ticker))

    if to_fetch:
        logger.info(f"  Fetching fundamental data for {len(to_fetch)} new ticker(s)...")
        completed = 0
        with ThreadPoolExecutor(max_workers=config.YAHOO_MAX_WORKERS) as executor:
            future_to_item = {
                executor.submit(_fetch_fundamental_one, ticker): (isin, ticker)
                for isin, ticker in to_fetch
            }
            for future in as_completed(future_to_item):
                isin, ticker = future_to_item[future]
                result = future.result()

                rows.append({
                    "ISIN": isin, "Yahoo Ticker": ticker,
                    "Market Cap": result["Market Cap"],
                    "PE Ratio": result["PE Ratio"],
                    "PB Ratio": result["PB Ratio"],
                    "ROE": result["ROE"],
                    "Dividend Yield": result["Dividend Yield"],
                    "Debt to Equity": result["Debt to Equity"],
                })

                if use_cache:
                    cache[ticker] = result

                completed += 1
                if use_cache and completed % 10 == 0:
                    _save_fundamental_cache(cache)

        if use_cache:
            _save_fundamental_cache(cache)

    original_order = {isin: i for i, isin in enumerate(mapping["ISIN"])}
    rows.sort(key=lambda r: original_order.get(r["ISIN"], 0))

    return pd.DataFrame(rows)