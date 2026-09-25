# Fund / Portfolio Performance Tracker

A Python-based fund research and portfolio analytics platform that turns
fund NAV, benchmark, and portfolio-weight data into performance, risk,
portfolio-structure, attribution, fundamental, and holdings-change analysis.

The project provides both:

- an interactive **Streamlit research dashboard**
- a **Python CLI pipeline** that generates Excel reports

It is designed around fund holdings and NAV snapshots rather than relying
on a hardcoded fund or portfolio.

---

## What it does

### Performance analysis

For each fund, the system calculates:

- Daily returns
- Cumulative returns
- Absolute return
- CAGR
- Benchmark return
- Active return
- Tracking error
- Information ratio
- Jensen's alpha
- Beta
- Maximum drawdown
- Period-based performance

### Risk analytics

The dashboard provides:

- Annualised volatility
- Sharpe ratio
- Sortino ratio
- Downside deviation
- Beta
- Jensen's alpha
- Rolling volatility
- Rolling Sharpe ratio
- Drawdown analysis

Risk-free rate and other relevant settings are configurable through
`config.py` / environment configuration.

### Multi-fund research

Multiple configured funds can be compared using:

- Fund return
- Benchmark return
- Active return
- Risk metrics
- Drawdown
- CAGR
- Tracking error
- Information ratio
- Number of holdings
- Latest portfolio snapshot

### Portfolio analytics

For a selected fund and snapshot, the system analyzes:

- Number of holdings
- Top holding weight
- Top-5 concentration
- Top-10 concentration
- Herfindahl-Hirschman Index (HHI)
- Effective number of holdings
- Sector allocation
- Market-cap allocation
- Holdings overlap between funds
- Portfolio changes between snapshots

### Attribution analysis

The system estimates portfolio contribution using:

`Contribution = Portfolio Weight × Stock Return`

It provides:

- Stock-level contribution
- Sector-level contribution
- Top contributors
- Bottom contributors
- Monthly historical attribution
- Monthly sector attribution
- Attribution audit/status information

Historical attribution uses each month's portfolio snapshot and the
corresponding historical return window.

### Holdings changes

The system compares portfolio snapshots and classifies holdings as:

- New
- Exited
- Increased
- Reduced
- Unchanged

Weight change is calculated from the difference between current and
previous portfolio weights.

This is a holdings-change analysis and does not attempt to infer actual
trade transactions.

### Fundamental research

For supported securities, Yahoo Finance data can provide:

- Market capitalisation
- P/E ratio
- P/B ratio
- ROE
- Dividend yield
- Debt-to-equity
- Sector
- Industry

ISINs are resolved to Yahoo Finance tickers using NSE and BSE Security
Master files.

Yahoo-derived data is cached locally and fetched with retry/rate-limit
handling so temporary failures do not stop the entire analysis.

### Excel reporting

The CLI pipeline can generate formatted Excel reports containing:

- Performance analysis
- NAV and benchmark charts
- Growth charts
- Drawdown charts
- Portfolio/sector information
- Stock contribution
- Holdings/rebalancing analysis

Generated reports are written to the local `Outputs/` directory.

`Outputs/` is intentionally excluded from Git because reports are generated
artifacts rather than source files.

---

## Dashboard

The Streamlit dashboard is divided into research-oriented sections:

- Performance
- Risk Analytics
- Fund Research Comparison
- Fund Research Detail
- Portfolio Analytics
- Fundamental Research
- Historical Attribution & Holdings Changes
- Attribution

The sidebar handles:

- Adding funds
- Removing funds
- Selecting funds
- Selecting portfolio snapshots
- Updating NSE/BSE Security Masters
- Configuring the rebalance/drift threshold

Launch the dashboard with:

```bash
cd fund_tracker
python -m streamlit run dashboard.py
