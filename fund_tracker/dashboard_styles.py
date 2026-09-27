"""
dashboard_styles.py
-------------------
Institutional terminal styling and design tokens.
Inspired by structur-al: sharp, minimal, high-density, typography-driven financial interface.
"""

def get_theme_tokens(dark_mode: bool = True) -> dict:
    """Return color, typography, and border tokens for dark and light themes."""
    if dark_mode:
        return {
            "background": "#080B10",
            "surface": "#0E131C",
            "surface_elevated": "#141C28",
            "surface_subtle": "#0B0F17",
            "border": "#1B2433",
            "border_subtle": "#141B26",
            "border_focus": "#388BFD",
            "text": "#E6EDF3",
            "text_muted": "#7D8B9F",
            "text_dim": "#4B5668",
            "accent": "#388BFD",
            "accent_subtle": "rgba(56, 139, 253, 0.10)",
            "positive": "#2EA043",
            "positive_bg": "rgba(46, 160, 67, 0.12)",
            "negative": "#F85149",
            "negative_bg": "rgba(248, 81, 73, 0.12)",
            "warning": "#D29922",
            "warning_bg": "rgba(210, 153, 34, 0.12)",
        }
    else:
        return {
            "background": "#F6F8FA",
            "surface": "#FFFFFF",
            "surface_elevated": "#F0F2F5",
            "surface_subtle": "#EAECEF",
            "border": "#D0D7DE",
            "border_subtle": "#E1E4E8",
            "border_focus": "#0969DA",
            "text": "#1F2328",
            "text_muted": "#57606A",
            "text_dim": "#8C959F",
            "accent": "#0969DA",
            "accent_subtle": "rgba(9, 105, 218, 0.08)",
            "positive": "#1A7F37",
            "positive_bg": "rgba(26, 127, 55, 0.08)",
            "negative": "#CF222E",
            "negative_bg": "rgba(207, 34, 46, 0.08)",
            "warning": "#9A6700",
            "warning_bg": "rgba(154, 103, 0, 0.08)",
        }


def get_application_css(dark_mode: bool = True) -> str:
    """Generate the complete CSS stylesheet for the application."""
    t = get_theme_tokens(dark_mode)

    return f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

    :root {{
        --bg-app: {t['background']};
        --surface: {t['surface']};
        --surface-elevated: {t['surface_elevated']};
        --surface-subtle: {t['surface_subtle']};
        --border: {t['border']};
        --border-subtle: {t['border_subtle']};
        --border-focus: {t['border_focus']};
        --text: {t['text']};
        --text-muted: {t['text_muted']};
        --text-dim: {t['text_dim']};
        --accent: {t['accent']};
        --accent-subtle: {t['accent_subtle']};
        --positive: {t['positive']};
        --positive-bg: {t['positive_bg']};
        --negative: {t['negative']};
        --negative-bg: {t['negative_bg']};
        --warning: {t['warning']};
        --warning-bg: {t['warning_bg']};
    }}

    /* ── Reset & Base ── */
    html, body, [data-testid="stAppViewContainer"],
    [data-testid="stAppViewContainer"] > .main {{
        background-color: var(--bg-app) !important;
        color: var(--text) !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        letter-spacing: -0.01em;
    }}

    .block-container {{
        padding-top: 3.5rem !important;
        padding-bottom: 3rem !important;
        max-width: 1560px !important;
    }}

    header[data-testid="stHeader"], [data-testid="stToolbar"] {{
        background-color: var(--bg-app) !important;
        border-bottom: none;
    }}

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {{
        background-color: var(--surface) !important;
        border-right: 1px solid var(--border-subtle) !important;
        padding-top: 1rem !important;
    }}
    [data-testid="stSidebar"] * {{
        color: var(--text);
    }}
    [data-testid="stSidebar"] hr {{
        margin: 0.75rem 0 !important;
        border-color: var(--border-subtle) !important;
    }}
    [data-testid="stSidebar"] [data-testid="stExpander"] {{
        background-color: transparent !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 4px !important;
        margin-bottom: 0.5rem !important;
    }}

    /* ── Custom Navigation Bar (via stRadio) ── */
    div[data-testid="stRadio"] div[role="radiogroup"] span[data-baseweb="radio"] {{
        display: none !important;
    }}
    div[data-testid="stRadio"] div[role="radiogroup"] {{
        gap: 0;
        border-bottom: 1px solid var(--border);
        padding-bottom: 0;
        margin-bottom: 0.5rem;
    }}
    div[data-testid="stRadio"] div[role="radiogroup"] label {{
        margin: 0;
        padding: 0.55rem 1.2rem;
        border-bottom: 2px solid transparent;
        border-radius: 0 !important;
        background: transparent !important;
        color: var(--text-muted) !important;
        font-family: 'Inter', sans-serif;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        cursor: pointer;
        transition: color 0.15s ease, border-color 0.15s ease;
    }}
    div[data-testid="stRadio"] div[role="radiogroup"] label:hover {{
        color: var(--text) !important;
    }}
    div[data-testid="stRadio"] div[role="radiogroup"] label[data-checked="true"] {{
        border-bottom-color: var(--accent);
        color: var(--text) !important;
        font-weight: 600 !important;
    }}

    /* ── Fund Header Strip ── */
    .fund-header {{
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        flex-wrap: wrap;
        gap: 0.75rem;
        padding: 0.5rem 0 0.75rem 0;
        margin-bottom: 0.25rem;
    }}
    .fund-header-name {{
        font-size: 1.3rem;
        font-weight: 700;
        color: var(--text);
        letter-spacing: -0.02em;
    }}
    .fund-header-meta {{
        display: flex;
        align-items: center;
        gap: 0.5rem;
        flex-wrap: wrap;
    }}
    .fund-header-chip {{
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        padding: 0.15rem 0.5rem;
        font-size: 0.7rem;
        font-family: 'JetBrains Mono', monospace;
        font-weight: 500;
        color: var(--text-muted);
        background: var(--surface-subtle);
        border-radius: 3px;
    }}

    /* ── Section Labels ── */
    .section-label {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.65rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: var(--text-dim);
        margin-bottom: 0.35rem;
    }}
    .section-title {{
        font-size: 1.15rem;
        font-weight: 700;
        color: var(--text);
        letter-spacing: -0.02em;
        margin: 0 0 0.5rem 0;
    }}

    /* ── Page Header (workspace title) ── */
    .page-header {{
        margin-bottom: 1.5rem;
    }}
    .page-header-label {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.65rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: var(--text-dim);
        margin-bottom: 0.2rem;
    }}
    .page-header-title {{
        font-size: 1.35rem;
        font-weight: 700;
        color: var(--text);
        letter-spacing: -0.02em;
        margin: 0;
    }}

    /* ── Hero Stat (Overview landing) ── */
    .hero-stat {{
        padding: 1.25rem 0;
    }}
    .hero-stat-label {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.68rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--text-muted);
        margin-bottom: 0.4rem;
    }}
    .hero-stat-value {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 2.4rem;
        font-weight: 700;
        line-height: 1;
        color: var(--text);
        letter-spacing: -0.03em;
        margin-bottom: 0.35rem;
    }}
    .hero-stat-delta {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.82rem;
        font-weight: 600;
    }}

    /* ── Inline Stat Row (typography-driven, no cards) ── */
    .stat-row {{
        display: flex;
        gap: 2rem;
        flex-wrap: wrap;
        padding: 0.5rem 0;
    }}
    .stat-item {{
        min-width: 100px;
    }}
    .stat-item-label {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.62rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--text-dim);
        margin-bottom: 0.15rem;
    }}
    .stat-item-value {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.05rem;
        font-weight: 700;
        color: var(--text);
        line-height: 1.2;
    }}

    /* ── Ledger / List ── */
    .ledger-container {{
        padding: 0.75rem 0;
    }}
    .ledger-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding-bottom: 0.4rem;
        margin-bottom: 0.4rem;
        border-bottom: 1px solid var(--border-subtle);
    }}
    .ledger-title {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--text);
    }}
    .ledger-row {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.35rem 0;
        border-bottom: 1px solid var(--border-subtle);
        font-size: 0.82rem;
    }}
    .ledger-row:last-child {{
        border-bottom: none;
    }}
    .ledger-name {{
        color: var(--text);
        font-weight: 500;
    }}
    .ledger-val {{
        font-family: 'JetBrains Mono', monospace;
        font-weight: 600;
        font-size: 0.82rem;
    }}

    /* ── Risk Matrix (2×4 grid with thin separators) ── */
    .risk-matrix {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 0;
        border: 1px solid var(--border-subtle);
        border-radius: 4px;
        background: var(--surface);
        margin-bottom: 1.25rem;
    }}
    .risk-matrix-cell {{
        padding: 0.75rem 0.9rem;
        border-right: 1px solid var(--border-subtle);
        border-bottom: 1px solid var(--border-subtle);
    }}
    .risk-matrix-cell:nth-child(4n) {{
        border-right: none;
    }}
    .risk-matrix-cell:nth-child(n+5) {{
        border-bottom: none;
    }}
    .risk-matrix-label {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.6rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--text-muted);
        margin-bottom: 0.2rem;
    }}
    .risk-matrix-value {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.15rem;
        font-weight: 700;
        color: var(--text);
    }}

    /* ── Streamlit metric overrides ── */
    [data-testid="stMetricLabel"] {{
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.65rem !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.06em !important;
        color: var(--text-muted) !important;
    }}
    [data-testid="stMetricValue"] {{
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 1.25rem !important;
        font-weight: 700 !important;
        color: var(--text) !important;
        letter-spacing: -0.02em !important;
    }}
    [data-testid="stMetricDelta"] {{
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.75rem !important;
    }}

    /* ── Tables — subtle, borderless ── */
    [data-testid="stDataFrame"] {{
        border: none !important;
        border-radius: 0 !important;
        background-color: transparent !important;
    }}

    /* ── Charts — no border, transparent background ── */
    [data-testid="stPlotlyChart"], [data-testid="stVegaLiteChart"] {{
        background-color: transparent !important;
        border: none !important;
        border-radius: 0 !important;
        padding: 0 !important;
    }}

    /* ── Thin horizontal divider ── */
    .thin-divider {{
        border: none;
        border-top: 1px solid var(--border-subtle);
        margin: 1rem 0;
    }}

    /* ── Tabs ── */
    [data-baseweb="tab-list"] {{
        border-bottom: 1px solid var(--border) !important;
        background-color: transparent !important;
        gap: 0.25rem;
    }}
    [data-baseweb="tab"] {{
        font-size: 0.78rem !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 500 !important;
        color: var(--text-muted) !important;
        padding: 0.4rem 0.85rem !important;
        border-radius: 3px 3px 0 0 !important;
    }}
    [data-baseweb="tab"][aria-selected="true"] {{
        color: var(--accent) !important;
        font-weight: 700 !important;
    }}
    [data-baseweb="tab-highlight"] {{
        background-color: var(--accent) !important;
        height: 2px !important;
    }}

    /* ── Form Controls & Buttons ── */
    button[kind="primary"] {{
        background-color: var(--accent) !important;
        color: #FFFFFF !important;
        border: none !important;
        font-weight: 600 !important;
        border-radius: 4px !important;
        font-size: 0.82rem !important;
    }}
    button[kind="secondary"] {{
        background-color: var(--surface-subtle) !important;
        color: var(--text) !important;
        border: 1px solid var(--border) !important;
        border-radius: 4px !important;
        font-size: 0.82rem !important;
    }}
    .stSelectbox > div > div, .stTextInput > div > div, .stNumberInput > div > div {{
        background-color: var(--surface-subtle) !important;
        border-color: var(--border) !important;
        color: var(--text) !important;
        border-radius: 4px !important;
        font-size: 0.82rem !important;
    }}
    </style>
    """
