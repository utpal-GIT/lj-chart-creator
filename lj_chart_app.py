"""
LJ Chart Creator with Westgard Rules
Clinical QC Levey-Jennings Chart Application
Built with Streamlit + Plotly
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, date, time
from pathlib import Path
import json
import io

# ─── Persistence (auto-save / auto-load) ─────────────────────────────────────
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
QC_DATA_FILE = DATA_DIR / "qc_data.json"
CONFIG_FILE = DATA_DIR / "config_data.json"


def save_qc_data(df):
    """Save QC data DataFrame to JSON."""
    records = df.copy()
    records["Date"] = records["Date"].astype(str)
    records.to_json(QC_DATA_FILE, orient="records", indent=2)


def load_qc_data():
    """Load QC data from JSON if it exists."""
    if QC_DATA_FILE.exists():
        try:
            df = pd.read_json(QC_DATA_FILE, orient="records")
            if len(df) == 0:
                return None

            # Ensure correct column order and types
            expected_cols = ["Include", "Analyzer ID", "Parameter", "Date", "QC Lot", "Reagent Lot", "QC Result"]
            for col in expected_cols:
                if col not in df.columns:
                    df[col] = "" if col != "Include" else True

            # Fix types to match what st.data_editor expects
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            # Ensure Include is properly boolean — treat None/NaN as True
            df["Include"] = df["Include"].map(lambda x: True if x is None or (isinstance(x, float) and pd.isna(x)) else bool(x))
            df["Include"] = pd.array(df["Include"].tolist(), dtype="boolean")
            for col in ["Analyzer ID", "Parameter", "QC Lot", "Reagent Lot", "QC Result"]:
                df[col] = df[col].fillna("").astype(str).replace("None", "").replace("nan", "")

            return df[expected_cols]
        except Exception:
            pass
    return None


def save_config_data(config):
    """Save config dict to JSON."""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def load_config_data():
    """Load config dict from JSON if it exists."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return None


# ─── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="LJ Chart Creator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Hide sidebar completely */
    [data-testid="stSidebar"] { display: none; }
    [data-testid="collapsedControl"] { display: none; }

    /* Tighten main container */
    .block-container { padding-top: 0.5rem; padding-bottom: 0; max-width: 100%; }

    /* App header bar */
    .app-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 60%, #334155 100%);
        color: white;
        padding: 14px 28px;
        border-radius: 10px;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 16px;
    }
    .app-header h1 {
        color: white; margin: 0; font-size: 1.4em; font-weight: 700;
    }
    .app-header span {
        color: #94a3b8; font-size: 0.85em; margin-left: 8px;
    }

    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        background: #f1f5f9;
        border-radius: 8px;
        padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 8px 28px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.9em;
    }
    .stTabs [aria-selected="true"] {
        background: white !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }

    /* Section headers */
    .section-title {
        font-size: 0.95em;
        font-weight: 700;
        color: #1e293b;
        margin: 0 0 8px 0;
        padding: 8px 12px;
        background: #f8fafc;
        border-radius: 6px;
        border-left: 3px solid #3b82f6;
    }

    /* Violation cards */
    .violation-card {
        background: #fef2f2;
        border-left: 4px solid #ef4444;
        padding: 10px 14px;
        margin: 6px 0;
        border-radius: 0 6px 6px 0;
        font-size: 0.85em;
        line-height: 1.5;
    }
    .violation-card-warn {
        background: #fffbeb;
        border-left: 4px solid #f59e0b;
        padding: 10px 14px;
        margin: 6px 0;
        border-radius: 0 6px 6px 0;
        font-size: 0.85em;
        line-height: 1.5;
    }

    /* Metric row */
    .metric-row {
        display: flex;
        gap: 8px;
        margin-bottom: 10px;
    }
    .metric-box {
        flex: 1;
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 10px 12px;
        text-align: center;
    }
    .metric-box .label {
        font-size: 0.65em;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 600;
    }
    .metric-box .val {
        font-size: 1.3em;
        font-weight: 700;
        color: #1e293b;
        margin-top: 2px;
    }

    /* Filter bar */
    .filter-bar {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 10px;
    }

    /* Hide default streamlit elements */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }

    /* Compact data editor — force left-align ALL cells including numbers */
    .stDataEditor { border-radius: 6px; overflow: hidden; }
    .stDataEditor [role="gridcell"],
    .stDataEditor [role="gridcell"] * ,
    .stDataEditor [data-testid="StyledDataFrameDataCell"],
    .stDataEditor [data-testid="StyledDataFrameDataCell"] * {
        text-align: left !important;
        justify-content: flex-start !important;
    }
    .stDataEditor [role="gridcell"] input {
        text-align: left !important;
    }
    .stDataEditor [role="columnheader"],
    .stDataEditor [role="columnheader"] * {
        text-align: left !important;
        justify-content: flex-start !important;
    }
    /* Override glide-data-grid number cell right-alignment */
    .stDataEditor canvas + div [style*="text-align"],
    .stDataEditor div[data-testid="glideDataEditor"] * {
        text-align: left !important;
    }

    /* Center-aligned config table */
    .config-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 14px;
        color: #1e293b;
    }
    .config-table th {
        text-align: center;
        padding: 10px 12px;
        background: #f1f5f9;
        font-weight: 600;
        border-bottom: 2px solid #e2e8f0;
    }
    .config-table td {
        text-align: center;
        padding: 10px 12px;
        border-bottom: 1px solid #e2e8f0;
    }
    .config-table tr:hover td {
        background: #f8fafc;
    }

    /* Westgard legend */
    .westgard-legend {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        padding: 8px 0;
        font-size: 0.78em;
    }
    .wg-badge {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 3px 10px;
        border-radius: 12px;
        font-weight: 600;
    }
    .wg-warn { background: #fef3c7; color: #92400e; }
    .wg-reject { background: #fee2e2; color: #991b1b; }

    /* Config table */
    .config-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

# ─── Undo/Redo JS injection for data editor ─────────────────────────────────
# Streamlit's data_editor blocks Ctrl+Z/Y at the app level; this re-enables it
# inside the ag-grid cells by intercepting keydown before Streamlit captures it.
st.markdown("""
<script>
document.addEventListener('keydown', function(e) {
    const target = e.target;
    const isEditable = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA'
        || target.isContentEditable || target.closest('[role="gridcell"]');
    if (isEditable && (e.ctrlKey || e.metaKey)) {
        if (e.key === 'z' || e.key === 'y') {
            e.stopPropagation();
        }
    }
}, true);
</script>
""", unsafe_allow_html=True)


# ─── Session State Initialization ──────────────────────────────────────────────
def init_session_state():
    if "qc_data" not in st.session_state:
        saved = load_qc_data()
        if saved is not None:
            st.session_state.qc_data = saved
        else:
            st.session_state.qc_data = pd.DataFrame({
                "Include": pd.array([True] * 10, dtype="boolean"),
                "Analyzer ID": [""] * 10,
                "Parameter": [""] * 10,
                "Date": [datetime.now().replace(second=0, microsecond=0)] * 10,
                "QC Lot": [""] * 10,
                "Reagent Lot": [""] * 10,
                "QC Result": [""] * 10,
            })
    if "config_data" not in st.session_state:
        saved_cfg = load_config_data()
        st.session_state.config_data = saved_cfg if saved_cfg else {}

init_session_state()


# ─── Westgard Rules Engine ────────────────────────────────────────────────────
def compute_z_scores(values, mean, sd):
    if sd == 0:
        return [0.0] * len(values)
    return [(v - mean) / sd for v in values]


def apply_westgard_rules(values, mean, sd):
    n = len(values)
    z = compute_z_scores(values, mean, sd)
    results = []

    for i in range(n):
        violations = []
        severity = "pass"

        # 1-3s: Single point beyond +/-3SD
        if abs(z[i]) > 3:
            violations.append({
                "rule": "1-3s",
                "type": "reject",
                "description": f"Value {values[i]:.2f} exceeds +/-3SD (z={z[i]:.2f})",
                "troubleshoot": "Immediate rejection. Check for: sample contamination, reagent degradation, "
                                "calibration drift, instrument malfunction, or wrong QC material. "
                                "Re-run the QC after troubleshooting. Do NOT report patient results."
            })
            severity = "reject"

        # 1-2s: Single point beyond +/-2SD (warning only)
        elif abs(z[i]) > 2:
            violations.append({
                "rule": "1-2s",
                "type": "warning",
                "description": f"Value {values[i]:.2f} exceeds +/-2SD (z={z[i]:.2f})",
                "troubleshoot": "Warning rule - triggers inspection of additional rules. "
                                "If no other rules are violated, this is acceptable. "
                                "Monitor the next few QC runs closely for trends."
            })
            severity = "warning"

        # 2-2s: Two consecutive beyond +/-2SD on same side
        if i >= 1:
            if (z[i] > 2 and z[i-1] > 2) or (z[i] < -2 and z[i-1] < -2):
                violations.append({
                    "rule": "2-2s",
                    "type": "reject",
                    "description": "Two consecutive values beyond +/-2SD on the same side",
                    "troubleshoot": "Systematic error detected. Check for: calibration shift, "
                                    "reagent lot change, deteriorated QC material, or environmental changes "
                                    "(temperature, humidity). Recalibrate and re-run QC."
                })
                severity = "reject"

        # R-4s: Range between consecutive > 4SD
        if i >= 1:
            if abs(z[i] - z[i-1]) > 4:
                violations.append({
                    "rule": "R-4s",
                    "type": "reject",
                    "description": f"Range between consecutive points exceeds 4SD (delta_z={abs(z[i]-z[i-1]):.2f})",
                    "troubleshoot": "Random error detected. Check for: pipetting error, air bubbles, "
                                    "sample mix-up, intermittent instrument malfunction, or "
                                    "incomplete mixing of reagents. Repeat both QC levels."
                })
                severity = "reject"

        # 4-1s: Four consecutive beyond +/-1SD on same side
        if i >= 3:
            last4 = z[i-3:i+1]
            if all(v > 1 for v in last4) or all(v < -1 for v in last4):
                violations.append({
                    "rule": "4-1s",
                    "type": "reject",
                    "description": "Four consecutive values beyond +/-1SD on the same side",
                    "troubleshoot": "Systematic shift developing. Check for: gradual calibration drift, "
                                    "aging reagents, environmental changes, or QC material near expiry. "
                                    "Consider recalibration with fresh calibrator."
                })
                severity = "reject"

        # 10x: Ten consecutive on same side of mean
        if i >= 9:
            last10 = z[i-9:i+1]
            if all(v > 0 for v in last10) or all(v < 0 for v in last10):
                violations.append({
                    "rule": "10x",
                    "type": "reject",
                    "description": "Ten consecutive values on the same side of the mean",
                    "troubleshoot": "Significant systematic bias. Check for: need for recalibration, "
                                    "QC target value may need updating, reagent lot drift, or "
                                    "instrument maintenance required. Review assigned mean and SD values."
                })
                severity = "reject"

        results.append({
            "index": i,
            "value": values[i],
            "z_score": z[i],
            "violations": violations,
            "severity": severity,
        })

    return results


# ─── Helper ──────────────────────────────────────────────────────────────────
def get_config_key(parameter, qc_lot):
    return f"{parameter}||{qc_lot}"


def build_lj_chart(df, mean, sd, parameter, qc_lot, westgard_results):
    fig = go.Figure()
    dates = pd.to_datetime(df["Date"]).dt.strftime("%d %b %Y, %H:%M").tolist()
    values = df["QC Result"].tolist()

    # Modern color palette
    CLR_REJECT_BAND = 'rgba(239,68,68,0.12)'    # soft red
    CLR_WARN_BAND   = 'rgba(251,191,36,0.14)'   # soft amber
    CLR_PASS_BAND   = 'rgba(52,211,153,0.13)'   # soft emerald
    CLR_MEAN_LINE   = '#0f172a'                  # slate-900
    CLR_1SD_LINE    = '#6366f1'                  # indigo-500
    CLR_2SD_LINE    = '#f59e0b'                  # amber-500
    CLR_3SD_LINE    = '#ef4444'                  # red-500
    CLR_TREND       = '#3b82f6'                  # blue-500
    CLR_PASS_PT     = '#10b981'                  # emerald-500
    CLR_WARN_PT     = '#f97316'                  # orange-500
    CLR_REJECT_PT   = '#ef4444'                  # red-500

    # SD bands — soft gradient zones
    band_specs = [
        (3, 2, CLR_REJECT_BAND),
        (2, 1, CLR_WARN_BAND),
        (1, -1, CLR_PASS_BAND),
        (-1, -2, CLR_WARN_BAND),
        (-2, -3, CLR_REJECT_BAND),
    ]
    for top_m, bot_m, color in band_specs:
        fig.add_trace(go.Scatter(
            x=dates, y=[mean + top_m * sd] * len(dates),
            mode='lines', line=dict(width=0), showlegend=False, hoverinfo='skip'
        ))
        fig.add_trace(go.Scatter(
            x=dates, y=[mean + bot_m * sd] * len(dates),
            mode='lines', line=dict(width=0), fill='tonexty',
            fillcolor=color, showlegend=False, hoverinfo='skip'
        ))

    # Control limit lines — NO legend, labels go on Y-axis
    line_specs = [
        (3, CLR_3SD_LINE, "dash", 1.5),
        (2, CLR_2SD_LINE, "dashdot", 1.5),
        (1, CLR_1SD_LINE, "dot", 1.2),
        (0, CLR_MEAN_LINE, "solid", 2.5),
        (-1, CLR_1SD_LINE, "dot", 1.2),
        (-2, CLR_2SD_LINE, "dashdot", 1.5),
        (-3, CLR_3SD_LINE, "dash", 1.5),
    ]
    for mult, color, dash, width in line_specs:
        val = mean + mult * sd
        fig.add_trace(go.Scatter(
            x=dates, y=[val] * len(dates),
            mode='lines',
            line=dict(color=color, width=width, dash=dash),
            showlegend=False,
            hoverinfo='skip',
        ))

    # Trend line
    fig.add_trace(go.Scatter(
        x=dates, y=values,
        mode='lines',
        name='Trend',
        line=dict(color=CLR_TREND, width=2.5),
        hoverinfo='skip',
    ))

    # ── Group color palette (distinct, modern colors) ─────────────────────────
    GROUP_COLORS = [
        '#3b82f6',  # blue-500
        '#10b981',  # emerald-500
        '#8b5cf6',  # violet-500
        '#f97316',  # orange-500
        '#06b6d4',  # cyan-500
        '#ec4899',  # pink-500
        '#84cc16',  # lime-500
        '#f43f5e',  # rose-500
        '#14b8a6',  # teal-500
        '#a855f7',  # purple-500
        '#eab308',  # yellow-500
        '#6366f1',  # indigo-500
    ]

    # Severity → marker shape & size
    SEVERITY_SHAPE = {
        'pass':    ('circle', 10),
        'warning': ('diamond', 13),
        'reject':  ('x', 14),
    }

    # Build group keys from DataFrame columns (clean None/NaN/empty to "")
    def _clean(val):
        s = str(val).strip() if val is not None else ""
        return "" if s.lower() in ("", "none", "nan", "nat") else s

    analyzers = [_clean(v) for v in (df["Analyzer ID"].tolist() if "Analyzer ID" in df.columns else [""] * len(df))]
    reagents = [_clean(v) for v in (df["Reagent Lot"].tolist() if "Reagent Lot" in df.columns else [""] * len(df))]
    group_keys = []
    for a, r in zip(analyzers, reagents):
        if a and r:
            group_keys.append(f"{a} | {r}")
        elif a:
            group_keys.append(a)
        elif r:
            group_keys.append(r)
        else:
            group_keys.append("Default")

    # Get unique groups in order of appearance
    seen = set()
    unique_groups = []
    for g in group_keys:
        if g not in seen:
            seen.add(g)
            unique_groups.append(g)
    group_color_map = {g: GROUP_COLORS[i % len(GROUP_COLORS)] for i, g in enumerate(unique_groups)}

    # Only show group legend if more than one group exists
    show_group_legend = len(unique_groups) > 1

    # Track which groups already have a legend entry (one per group)
    group_legend_shown = set()

    # Data points — color by group, shape by severity
    for sev in ['pass', 'warning', 'reject']:
        symbol, size = SEVERITY_SHAPE[sev]
        indices = [i for i, r in enumerate(westgard_results) if r["severity"] == sev]
        if not indices:
            continue

        # Sub-group by Analyzer+Reagent combo within this severity
        sub_groups = {}
        for i in indices:
            gk = group_keys[i]
            if gk not in sub_groups:
                sub_groups[gk] = []
            sub_groups[gk].append(i)

        for gk, idx_list in sub_groups.items():
            color = group_color_map[gk]
            border_color = 'white' if sev == 'pass' else ('#7c2d12' if sev == 'warning' else '#991b1b')
            border_width = 1.5 if sev == 'pass' else (2 if sev == 'warning' else 3)

            # Legend: show group name if multiple groups, otherwise show severity
            if show_group_legend:
                show_in_legend = gk not in group_legend_shown
                legend_name = gk
                group_legend_shown.add(gk)
            else:
                show_in_legend = True
                legend_name = sev.capitalize() if sev != 'reject' else 'REJECT'
                if sev == 'warning':
                    legend_name = 'Warning (1-2s)'

            if sev == 'pass':
                cdata = [f"z={westgard_results[i]['z_score']:.2f}" for i in idx_list]
                htpl = "<b>%{x}</b><br>Value: %{y:.2f}<br>%{customdata}<extra>" + gk + " · Pass</extra>"
            else:
                cdata = [", ".join([v["rule"] for v in westgard_results[i]["violations"]]) for i in idx_list]
                htpl = "<b>%{x}</b><br>Value: %{y:.2f}<br>Rules: %{customdata}<extra>" + gk + " · " + sev.upper() + "</extra>"

            fig.add_trace(go.Scatter(
                x=[dates[i] for i in idx_list],
                y=[values[i] for i in idx_list],
                mode='markers',
                name=legend_name,
                showlegend=show_in_legend,
                legendgroup=gk if show_group_legend else sev,
                marker=dict(color=color, size=size, symbol=symbol,
                            line=dict(width=border_width, color=border_color)),
                customdata=cdata,
                hovertemplate=htpl,
            ))

    # Y-axis tick values: show SD labels on the axis itself
    sd_ticks = [
        (mean - 3*sd, f"-3SD ({mean - 3*sd:.1f})"),
        (mean - 2*sd, f"-2SD ({mean - 2*sd:.1f})"),
        (mean - 1*sd, f"-1SD ({mean - 1*sd:.1f})"),
        (mean,        f"Mean ({mean:.1f})"),
        (mean + 1*sd, f"+1SD ({mean + 1*sd:.1f})"),
        (mean + 2*sd, f"+2SD ({mean + 2*sd:.1f})"),
        (mean + 3*sd, f"+3SD ({mean + 3*sd:.1f})"),
    ]
    tick_vals = [t[0] for t in sd_ticks]
    tick_text = [t[1] for t in sd_ticks]

    y_pad = sd * 1.5
    y_min = min(mean - 3 * sd - y_pad, min(values) - y_pad) if values else mean - 4 * sd
    y_max = max(mean + 3 * sd + y_pad, max(values) + y_pad) if values else mean + 4 * sd

    fig.update_layout(
        title=dict(
            text=f"<b>{parameter}</b>  ·  QC Lot: {qc_lot}",
            font=dict(size=18, color="#0f172a", family="Arial Black"),
            x=0.5,
            xanchor="center",
            yanchor="top",
            y=0.98,
            pad=dict(b=25),
            xref="paper",
        ),
        xaxis=dict(
            title=dict(text="<b>Date</b>", font=dict(size=14, color="#1e293b")),
            showgrid=True, gridcolor='rgba(0,0,0,0.06)',
            tickangle=-45, tickfont=dict(size=11, color="#1e293b"),
        ),
        yaxis=dict(
            title=dict(text="<b>QC Result</b>", font=dict(size=14, color="#1e293b")),
            showgrid=True, gridcolor='rgba(0,0,0,0.06)',
            range=[y_min, y_max],
            tickvals=tick_vals,
            ticktext=tick_text,
            tickfont=dict(size=11, color="#1e293b"),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.005,
            xanchor="center",
            x=0.50,
            xref="paper",
            font=dict(size=12, color="#1e293b"),
            bgcolor="rgba(255,255,255,0)",
            borderwidth=0,
        ),
        plot_bgcolor='#f8fafc',
        paper_bgcolor='white',
        hovermode='x unified',
        height=560,
        margin=dict(l=120, r=30, t=90, b=100),
    )

    return fig


# ═══════════════════════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="app-header">
    <h1>📊 LJ Chart Creator</h1>
    <span>Clinical QC Management with Westgard Rules</span>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TOP TABS
# ═══════════════════════════════════════════════════════════════════════════════
tab_chart, tab_config = st.tabs(["📈  LJ Chart", "⚙️  LJ Configurer"])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1: LJ CHART
# ═══════════════════════════════════════════════════════════════════════════════
with tab_chart:

    # Westgard rules legend bar
    st.markdown("""
    <div class="westgard-legend">
        <span class="wg-badge wg-warn">1-2s Warning</span>
        <span class="wg-badge wg-reject">1-3s Reject</span>
        <span class="wg-badge wg-reject">2-2s Reject</span>
        <span class="wg-badge wg-reject">R-4s Reject</span>
        <span class="wg-badge wg-reject">4-1s Reject</span>
        <span class="wg-badge wg-reject">10x Reject</span>
    </div>
    """, unsafe_allow_html=True)

    # Import / Sample bar (compact)
    with st.expander("Import / Export / Sample Data", expanded=False):
        ic1, ic2, ic3 = st.columns(3)
        with ic1:
            uploaded_file = st.file_uploader("Import CSV", type=["csv"], label_visibility="collapsed")
            if uploaded_file is not None:
                try:
                    imported_df = pd.read_csv(uploaded_file)
                    required_cols = {"Parameter", "Date", "QC Lot", "Reagent Lot", "QC Result"}
                    if required_cols.issubset(set(imported_df.columns)):
                        imported_df["Include"] = True
                        if "Analyzer ID" not in imported_df.columns:
                            imported_df["Analyzer ID"] = ""
                        imported_df["Date"] = pd.to_datetime(imported_df["Date"])
                        imported_df["QC Result"] = imported_df["QC Result"].astype(str)
                        st.session_state.qc_data = imported_df[["Include", "Analyzer ID", "Parameter", "Date", "QC Lot", "Reagent Lot", "QC Result"]]
                        save_qc_data(st.session_state.qc_data)
                        st.success(f"Imported {len(imported_df)} rows!")
                        st.rerun()
                    else:
                        st.error(f"CSV must have columns: {required_cols}")
                except Exception as e:
                    st.error(f"Error: {e}")
        with ic2:
            if len(st.session_state.qc_data) > 0:
                csv_out = st.session_state.qc_data.drop(columns=["Include"]).to_csv(index=False)
                st.download_button("Export Data (CSV)", data=csv_out, file_name="qc_data.csv",
                                   mime="text/csv", use_container_width=True)
        with ic3:
            if st.button("Load Sample Data", use_container_width=True):
                np.random.seed(42)
                sdates = pd.date_range("2024-01-01", periods=30, freq="D")
                svals = np.random.normal(5.5, 0.15, 30)
                svals[7] = 6.1; svals[15] = 5.9; svals[16] = 5.95; svals[22] = 5.0
                st.session_state.qc_data = pd.DataFrame({
                    "Include": pd.array([True]*30, dtype="boolean"),
                    "Analyzer ID": ["AU-5800"]*30,
                    "Parameter": ["Glucose"]*30,
                    "Date": [d.to_pydatetime().replace(hour=8, minute=30) for d in sdates],
                    "QC Lot": ["LOT-2024-001"]*30,
                    "Reagent Lot": ["RGT-A1"]*15 + ["RGT-A2"]*15,
                    "QC Result": [str(v) for v in np.round(svals, 2).tolist()],
                })
                key = get_config_key("Glucose", "LOT-2024-001")
                st.session_state.config_data[key] = {"parameter": "Glucose", "qc_lot": "LOT-2024-001", "mean": 5.5, "sd": 0.15}
                save_qc_data(st.session_state.qc_data)
                save_config_data(st.session_state.config_data)
                st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 1: DATA TABLE (full width, rendered first so edited_df is available)
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown('<div class="section-title">QC Data Entry</div>', unsafe_allow_html=True)

    # Table action buttons
    bc1, bc2, bc3, bc_spacer = st.columns([1, 1, 1, 5])
    with bc1:
        if st.button("+ Add Row", use_container_width=True):
            new_row = pd.DataFrame({
                "Include": pd.array([True], dtype="boolean"),
                "Analyzer ID": [""],
                "Parameter": [""],
                "Date": [datetime.now().replace(second=0, microsecond=0)],
                "QC Lot": [""],
                "Reagent Lot": [""],
                "QC Result": [""],
            })
            st.session_state.qc_data = pd.concat([st.session_state.qc_data, new_row], ignore_index=True)
            save_qc_data(st.session_state.qc_data)
            st.rerun()
    with bc2:
        if st.button("Select All", use_container_width=True):
            st.session_state.qc_data["Include"] = True
            save_qc_data(st.session_state.qc_data)
            st.rerun()
    with bc3:
        if st.button("Deselect All", use_container_width=True):
            st.session_state.qc_data["Include"] = False
            save_qc_data(st.session_state.qc_data)
            st.rerun()

    # Fixed height for 10 visible rows; extra rows scroll inside
    table_height = 400

    edited_df = st.data_editor(
        st.session_state.qc_data,
        num_rows="dynamic",
        use_container_width=True,
        height=table_height,
        column_config={
            "Include": st.column_config.CheckboxColumn("Include", default=True, width="small"),
            "Analyzer ID": st.column_config.TextColumn("Analyzer ID", width="medium"),
            "Parameter": st.column_config.TextColumn("Parameter", width="medium"),
            "Date": st.column_config.DatetimeColumn("Date", width="medium", format="D MMM YYYY, HH:mm"),
            "QC Lot": st.column_config.TextColumn("QC Lot", width="medium"),
            "Reagent Lot": st.column_config.TextColumn("Reagent Lot", width="medium"),
            "QC Result": st.column_config.TextColumn("QC Result", width="medium"),
        },
        key="data_editor",
    )
    # Clean None/NaN in text columns so they display as blank, not "None"
    for col in ["Analyzer ID", "Parameter", "QC Lot", "Reagent Lot", "QC Result"]:
        edited_df[col] = edited_df[col].fillna("").astype(str).replace("None", "").replace("nan", "")
    st.session_state.qc_data = edited_df
    save_qc_data(edited_df)

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 2: FILTERS (built from edited_df so they detect current data)
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown('<div class="section-title">Filters</div>', unsafe_allow_html=True)

    # Build filter options from the CURRENT edited data
    all_analyzers = sorted([str(a) for a in edited_df["Analyzer ID"].dropna().unique() if str(a).strip()])
    all_params = sorted([p for p in edited_df["Parameter"].dropna().unique() if str(p).strip()])
    all_qc = sorted([str(l) for l in edited_df["QC Lot"].dropna().unique() if str(l).strip()])
    all_rgt = sorted([str(l) for l in edited_df["Reagent Lot"].dropna().unique() if str(l).strip()])

    fc0, fc1, fc2, fc3, fc4 = st.columns([2, 2, 2, 2, 3])
    with fc0:
        sel_analyzer = st.selectbox("Analyzer ID", ["All"] + list(all_analyzers))
    with fc1:
        sel_param = st.selectbox("Parameter *", [""] + list(all_params))
    with fc2:
        sel_qc = st.selectbox("QC Lot *", [""] + list(all_qc))
    with fc3:
        sel_rgt = st.selectbox("Reagent Lot", ["All"] + list(all_rgt))
    with fc4:
        date_range = st.date_input("Date Range", value=(), help="Select start and end dates")

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 3: LJ CHART (full width)
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown('<div class="section-title">Levey-Jennings Chart</div>', unsafe_allow_html=True)

    if not sel_param or not sel_qc:
        st.info("Select **Parameter** and **QC Lot** in the filters above to generate the LJ chart.")
    else:
        config_key = get_config_key(sel_param, sel_qc)
        if config_key not in st.session_state.config_data:
            st.error(f"No configuration found for **{sel_param}** / **{sel_qc}**. "
                     "Go to the **LJ Configurer** tab to set Mean and SD first.")
        else:
            config = st.session_state.config_data[config_key]
            mean_val = config["mean"]
            sd_val = config["sd"]

            # Filter data (convert QC Result to numeric in case it's text)
            work_df = edited_df.copy()
            work_df["QC Result"] = pd.to_numeric(work_df["QC Result"], errors='coerce')
            chart_df = work_df[
                (work_df["Include"] == True) &
                (work_df["Parameter"] == sel_param) &
                (work_df["QC Lot"] == sel_qc)
            ].copy()
            chart_df = chart_df.dropna(subset=["QC Result"])

            if sel_analyzer != "All":
                chart_df = chart_df[chart_df["Analyzer ID"].astype(str) == sel_analyzer]
            if sel_rgt != "All":
                chart_df = chart_df[chart_df["Reagent Lot"] == sel_rgt]
            if len(date_range) == 2:
                start_dt = pd.Timestamp(date_range[0])
                end_dt = pd.Timestamp(date_range[1]) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
                chart_df = chart_df[(chart_df["Date"] >= start_dt) & (chart_df["Date"] <= end_dt)]

            chart_df = chart_df.sort_values("Date").reset_index(drop=True)

            if len(chart_df) == 0:
                st.warning("No data points match the selected filters.")
            else:
                # Option to deselect specific data points from the chart
                point_labels = [f"#{i+1} | {pd.Timestamp(chart_df.iloc[i]['Date']).strftime('%d %b %Y, %H:%M')} | {float(chart_df.iloc[i]['QC Result']):.2f}"
                                for i in range(len(chart_df))]
                excluded = st.multiselect(
                    "Exclude data points from chart (click to deselect)",
                    options=point_labels,
                    default=[],
                    help="Select points to exclude from the LJ chart and Westgard analysis",
                )
                excluded_indices = [point_labels.index(e) for e in excluded]

                if excluded_indices:
                    chart_df = chart_df.drop(chart_df.index[excluded_indices]).reset_index(drop=True)

                if len(chart_df) == 0:
                    st.warning("All data points have been excluded.")
                    st.stop()

                values = chart_df["QC Result"].tolist()
                obs_mean = sum(values) / len(values)
                obs_std = (sum((v - obs_mean)**2 for v in values) / len(values)) ** 0.5
                obs_cv = (obs_std / obs_mean * 100) if obs_mean != 0 else 0

                # Metrics row
                st.markdown(f"""
                <div class="metric-row">
                    <div class="metric-box"><div class="label">Data Points</div><div class="val">{len(values)}</div></div>
                    <div class="metric-box"><div class="label">Target Mean</div><div class="val">{mean_val:.2f}</div></div>
                    <div class="metric-box"><div class="label">Target SD</div><div class="val">{sd_val:.4f}</div></div>
                    <div class="metric-box"><div class="label">Observed CV%</div><div class="val">{obs_cv:.1f}%</div></div>
                    <div class="metric-box"><div class="label">Obs. Mean</div><div class="val">{obs_mean:.2f}</div></div>
                    <div class="metric-box"><div class="label">Obs. SD</div><div class="val">{obs_std:.4f}</div></div>
                </div>
                """, unsafe_allow_html=True)

                # Westgard analysis
                westgard_results = apply_westgard_rules(values, mean_val, sd_val)

                # Chart (full width)
                fig = build_lj_chart(chart_df, mean_val, sd_val, sel_param, sel_qc, westgard_results)
                st.plotly_chart(fig, use_container_width=True, config={
                    'toImageButtonOptions': {
                        'format': 'png',
                        'filename': f'LJ_{sel_param}_{sel_qc}',
                        'height': 600, 'width': 1400, 'scale': 2,
                    },
                    'displayModeBar': True,
                })

                # Export buttons — PNG and CSV
                ex1, ex2, ex_spacer = st.columns([1, 1, 4])
                with ex1:
                    png_bytes = fig.to_image(format="png", width=1400, height=600, scale=2)
                    st.download_button("Download Chart (PNG)", data=png_bytes,
                                       file_name=f"LJ_{sel_param}_{sel_qc}.png", mime="image/png",
                                       use_container_width=True)
                with ex2:
                    st.download_button("Download Data (CSV)", data=chart_df.to_csv(index=False),
                                       file_name=f"QC_{sel_param}_{sel_qc}.csv", mime="text/csv",
                                       use_container_width=True)

                # ══════════════════════════════════════════════════════════════
                # SECTION 4: FAILURE ANALYSIS (full width, below chart)
                # ══════════════════════════════════════════════════════════════
                st.markdown('<div class="section-title">QC Failure Analysis & Troubleshooting</div>',
                            unsafe_allow_html=True)

                violations_found = [r for r in westgard_results if r["violations"]]

                if not violations_found:
                    st.success("All QC points are within acceptable limits. No Westgard rule violations.")
                else:
                    reject_n = sum(1 for r in westgard_results if r["severity"] == "reject")
                    warn_n = sum(1 for r in westgard_results if r["severity"] == "warning")

                    if reject_n > 0:
                        st.error(f"{reject_n} rejection(s) and {warn_n} warning(s) detected across {len(values)} data points.")
                    else:
                        st.warning(f"{warn_n} warning(s) detected across {len(values)} data points.")

                    for result in violations_found:
                        pt_date = chart_df.iloc[result["index"]]["Date"]
                        for v in result["violations"]:
                            css_class = "violation-card" if v["type"] == "reject" else "violation-card-warn"
                            icon = "X" if v["type"] == "reject" else "!"
                            label = "REJECT" if v["type"] == "reject" else "WARNING"
                            ts_label = "Troubleshooting" if v["type"] == "reject" else "Suggestion"
                            st.markdown(f"""<div class="{css_class}">
                                <strong>[{icon}] {v['rule']} {label}</strong> &mdash;
                                Point #{result['index']+1} | Date: {pt_date} |
                                Value: {result['value']:.2f} (z={result['z_score']:.2f})<br>
                                <em>{v['description']}</em><br>
                                <strong>{ts_label}:</strong> {v['troubleshoot']}
                            </div>""", unsafe_allow_html=True)

                    # Summary table
                    st.markdown("**Violation Summary**")
                    summary_rows = []
                    for r in violations_found:
                        for v in r["violations"]:
                            summary_rows.append({
                                "Pt#": r["index"]+1,
                                "Date": chart_df.iloc[r["index"]]["Date"],
                                "Value": f"{r['value']:.2f}",
                                "Z": f"{r['z_score']:.2f}",
                                "Rule": v["rule"],
                                "Type": v["type"].upper(),
                            })
                    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2: LJ CONFIGURER
# ═══════════════════════════════════════════════════════════════════════════════
with tab_config:

    st.info("Configure Mean and SD for each Parameter + QC Lot combination. This is required before generating LJ charts.")

    # Add config form
    st.markdown('<div class="section-title">Add / Update Configuration</div>', unsafe_allow_html=True)

    # Auto-extract unique Parameter and QC Lot values from the data table
    available_params = sorted([p for p in st.session_state.qc_data["Parameter"].dropna().unique() if str(p).strip()])
    available_lots = sorted([l for l in st.session_state.qc_data["QC Lot"].dropna().unique() if str(l).strip()])

    cc1, cc2, cc3, cc4, cc5 = st.columns([2, 2, 1.5, 1.5, 1])
    with cc1:
        if available_params:
            cfg_param = st.selectbox("Parameter", available_params, index=0)
        else:
            cfg_param = st.text_input("Parameter", placeholder="Enter data in LJ Chart tab first")
    with cc2:
        if available_lots:
            cfg_lot = st.selectbox("QC Lot", available_lots, index=0)
        else:
            cfg_lot = st.text_input("QC Lot", placeholder="Enter data in LJ Chart tab first")
    with cc3:
        cfg_mean = st.number_input("Mean", value=0.0, format="%.4f", step=0.01)
    with cc4:
        cfg_sd = st.number_input("SD", value=0.0, format="%.4f", step=0.01, min_value=0.0)
    with cc5:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Save", type="primary", use_container_width=True):
            if cfg_param.strip() and cfg_lot.strip() and cfg_sd > 0:
                key = get_config_key(cfg_param.strip(), cfg_lot.strip())
                st.session_state.config_data[key] = {
                    "parameter": cfg_param.strip(), "qc_lot": cfg_lot.strip(),
                    "mean": cfg_mean, "sd": cfg_sd,
                }
                save_config_data(st.session_state.config_data)
                st.success(f"Saved: {cfg_param} / {cfg_lot}")
                st.rerun()
            else:
                st.error("Fill in all fields. SD must be > 0.")

    # Show existing configs
    st.markdown('<div class="section-title">Existing Configurations</div>', unsafe_allow_html=True)

    if st.session_state.config_data:
        rows = []
        for key, cfg in st.session_state.config_data.items():
            m, s = cfg["mean"], cfg["sd"]
            rows.append({
                "Parameter": cfg["parameter"],
                "QC Lot": cfg["qc_lot"],
                "Mean": round(m, 4),
                "SD": round(s, 4),
                "Mean-1SD": round(m - s, 4),
                "Mean+1SD": round(m + s, 4),
                "Mean-2SD": round(m - 2*s, 4),
                "Mean+2SD": round(m + 2*s, 4),
                "Mean-3SD": round(m - 3*s, 4),
                "Mean+3SD": round(m + 3*s, 4),
            })
        config_df = pd.DataFrame(rows)
        st.markdown(
            config_df.to_html(index=False, classes="config-table", border=0),
            unsafe_allow_html=True,
        )

        # Delete
        del_opts = [f"{c['parameter']} | {c['qc_lot']}" for c in st.session_state.config_data.values()]
        del_keys = list(st.session_state.config_data.keys())
        dc1, dc2 = st.columns([3, 1])
        with dc1:
            del_choice = st.selectbox("Select to remove", del_opts)
        with dc2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Remove", use_container_width=True):
                idx = del_opts.index(del_choice)
                del st.session_state.config_data[del_keys[idx]]
                save_config_data(st.session_state.config_data)
                st.rerun()
    else:
        st.warning("No configurations yet. Add one above to get started.")

    # Import / Export
    st.markdown('<div class="section-title">Import / Export</div>', unsafe_allow_html=True)
    ie1, ie2 = st.columns(2)
    with ie1:
        if st.session_state.config_data:
            st.download_button("Export Configs (JSON)",
                               data=json.dumps(st.session_state.config_data, indent=2),
                               file_name="lj_config.json", mime="application/json",
                               use_container_width=True)
    with ie2:
        up_cfg = st.file_uploader("Import Configs (JSON)", type=["json"])
        if up_cfg is not None:
            try:
                imp = json.loads(up_cfg.read().decode())
                st.session_state.config_data.update(imp)
                save_config_data(st.session_state.config_data)
                st.success(f"Imported {len(imp)} configs!")
                st.rerun()
            except Exception as e:
                st.error(f"Invalid file: {e}")
