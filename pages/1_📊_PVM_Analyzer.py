"""
PVM Analyzer — Streamlit Web App (Page 1)
Pricing × Volume × Mix decomposition for week/month-over-week pricing analysis.

Author: Shadqi (Pricing Strategy Analyst, Astro)
"""
import io
import math
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from pvm_analyzer_v3 import analyze

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PVM Analyzer — Astro Pricing",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="auto",
)

# Custom CSS — minimal, focused on KPI cards & banner
st.markdown("""
<style>
    .main > div { padding-top: 1rem; }
    .kpi-card {
        border: 1px solid #E5E7EB;
        border-radius: 10px;
        padding: 16px 20px;
        background: #FFFFFF;
        height: 100%;
    }
    .kpi-label { font-size: 12px; color: #6B7280; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600; }
    .kpi-value { font-size: 28px; font-weight: 700; color: #111827; margin: 4px 0; }
    .kpi-delta-pos { font-size: 14px; color: #059669; font-weight: 600; }
    .kpi-delta-neg { font-size: 14px; color: #DC2626; font-weight: 600; }
    .kpi-delta-neu { font-size: 14px; color: #6B7280; font-weight: 600; }
    .kpi-sub { font-size: 11px; color: #9CA3AF; margin-top: 4px; }

    .banner-warn {
        background: #FEF3C7;
        border-left: 4px solid #F59E0B;
        padding: 12px 16px;
        border-radius: 6px;
        margin-bottom: 16px;
    }
    .banner-ok {
        background: #D1FAE5;
        border-left: 4px solid #10B981;
        padding: 12px 16px;
        border-radius: 6px;
        margin-bottom: 16px;
    }
    .banner-title { font-weight: 700; margin-bottom: 4px; }

    .section-header {
        font-size: 18px;
        font-weight: 700;
        color: #111827;
        margin-top: 24px;
        margin-bottom: 8px;
        padding-bottom: 4px;
        border-bottom: 2px solid #E5E7EB;
    }
    .section-sub { font-size: 13px; color: #6B7280; margin-bottom: 12px; }

    .mover-card {
        border: 1px solid #E5E7EB;
        border-radius: 6px;
        padding: 8px 12px;
        margin-bottom: 6px;
        background: #FFFFFF;
        font-size: 12px;
    }
    .mover-rank { font-weight: 700; color: #6B7280; }
    .mover-name { font-weight: 600; color: #111827; }
    .mover-gain { color: #059669; font-weight: 600; }
    .mover-loss { color: #DC2626; font-weight: 600; }
    .mover-meta { color: #6B7280; font-size: 11px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
REQUIRED_COLS = ['selling_price', 'selling_price1', 'cost_price', 'cost_price1', 'qty', 'qty1']
OPTIONAL_COLS = ['comp_price', 'comp_price1', 'pi', 'pi1', 'avg_stock', 'avg_stock1',
                 'pareto_classification', 'margin_pct', 'margin1_pct']
DIM_COLS = ['pricing_bl_25', 'l1_category_name', 'business_lines_2025']
PERIOD_PAIRS = [('week_key', 'next_week'), ('week_key', 'next_key'), ('month_key', 'next_month')]

BL_ORDER = ['Dry', 'Fresh', 'Frozen', 'PL']
BL_COLORS = {'Dry': '#3B82F6', 'Fresh': '#10B981', 'Frozen': '#06B6D4', 'PL': '#8B5CF6'}

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def fmt_rp(v, compact=True):
    """Format Indonesian Rupiah."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    av = abs(v)
    sign = "-" if v < 0 else ""
    if compact:
        if av >= 1e12: return f"{sign}{av/1e12:.2f} T"
        if av >= 1e9:  return f"{sign}{av/1e9:.2f} B"
        if av >= 1e6:  return f"{sign}{av/1e6:.1f} M"
        if av >= 1e3:  return f"{sign}{av/1e3:.0f} K"
    return f"{sign}{av:,.0f}"

def fmt_pct(v, decimals=2):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    return f"{v*100:.{decimals}f}%"

def fmt_pp(v, decimals=2):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    sign = "+" if v >= 0 else ""
    return f"{sign}{v*100:.{decimals}f}pp"

def kpi_card(label, value, delta=None, delta_label=None, sub=None, delta_inverse=False):
    """Render a KPI card. delta_inverse: True if lower is better (e.g. cost)."""
    if delta is None:
        delta_html = ""
    else:
        if delta > 0:
            css_class = "kpi-delta-neg" if delta_inverse else "kpi-delta-pos"
            arrow = "▲"
        elif delta < 0:
            css_class = "kpi-delta-pos" if delta_inverse else "kpi-delta-neg"
            arrow = "▼"
        else:
            css_class = "kpi-delta-neu"; arrow = "■"
        delta_html = f'<div class="{css_class}">{arrow} {delta_label}</div>'
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    # IMPORTANT: do NOT indent — Streamlit treats 4+ leading spaces as code blocks
    return (
        f'<div class="kpi-card">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div>'
        f'{delta_html}'
        f'{sub_html}'
        f'</div>'
    )

def detect_anomalies(pvm):
    """Return list of anomaly dicts. Trigger: GP Δ% < -3% OR qty Δ% < -4%."""
    anomalies = []
    for bl in BL_ORDER:
        d = pvm.get(bl)
        if not d: continue
        # Recompute pct changes
        gp_p1 = d.get('gp_start', 0)
        gp_p2 = d.get('gp_end', 0)
        gp_pct = (gp_p2 - gp_p1) / gp_p1 if gp_p1 else 0
        # For qty, we need to sum qty per BL — but pvm only has aggregated GV/GP.
        # Approximate qty pct via GV pct as proxy (since qty pct not directly stored).
        # We'll use GV pct change as approximation here, with note in label.
        gv_p1 = d.get('gv_start', 0)
        gv_p2 = d.get('gv_end', 0)
        gv_pct = (gv_p2 - gv_p1) / gv_p1 if gv_p1 else 0

        gp_diff = gp_p2 - gp_p1
        if gp_pct < -0.03 or gv_pct < -0.04:
            # Identify dominant driver
            pp_b = d.get('pp_B', 0)
            pp_cogs = d.get('pp_cogs', 0)
            pp_price = d.get('pp_price', 0)
            pp_vm = d.get('pp_volmix', 0)
            pp_g = d.get('pp_G', 0)
            pp_existing = pp_cogs + pp_price + pp_vm

            # Rp components
            rp_existing = d.get('cogs_rp', 0) + d.get('price_rp', 0) + d.get('volmix_rp', 0)
            volmix_rp = d.get('volmix_rp', 0)

            drivers = []
            if abs(volmix_rp) > 30e6 and volmix_rp < 0:
                drivers.append(f"Vol/Mix drag {fmt_rp(volmix_rp)} Rp")
            if gv_pct < -0.03:
                drivers.append(f"GV drop {gv_pct*100:.1f}%")

            anomalies.append({
                'bl': bl,
                'gp_pct': gp_pct,
                'gp_diff': gp_diff,
                'gv_pct': gv_pct,
                'drivers': drivers,
            })
    return anomalies

def get_bridge_steps(pvm, scope, mode):
    """
    Get bridge step values per scope (TOTAL/Dry/Fresh/Frozen/PL).
    mode: 'rp' (Rupiah), 'pp' (margin points × 100), 'pct' (growth % of GP_p1)
    Returns dict: {label: value, ...} for 5 effect steps.
    """
    d = pvm[scope]
    if mode == 'rp':
        return {
            '1. Churned SKU Effect': -d['gp_dep'],
            '2.1 COGS Effect': d['cogs_rp'],
            '2.2 Price Effect': d['price_rp'],
            '2.3 Vol/Mix Effect': d['volmix_rp'],
            '3. New SKU Effect': d['gp_new'],
        }
    elif mode == 'pp':
        return {
            '1. Churned SKU Effect': d['pp_B'] * 100,
            '2.1 COGS Effect': d['pp_cogs'] * 100,
            '2.2 Price Effect': d['pp_price'] * 100,
            '2.3 Vol/Mix Effect': d['pp_volmix'] * 100,
            '3. New SKU Effect': d['pp_G'] * 100,
        }
    else:  # pct (growth %)
        gp_p1 = d['gp_start'] if d['gp_start'] else 1
        return {
            '1. Churned SKU Effect': (-d['gp_dep']) / gp_p1 * 100,
            '2.1 COGS Effect': d['cogs_rp'] / gp_p1 * 100,
            '2.2 Price Effect': d['price_rp'] / gp_p1 * 100,
            '2.3 Vol/Mix Effect': d['volmix_rp'] / gp_p1 * 100,
            '3. New SKU Effect': d['gp_new'] / gp_p1 * 100,
        }


def fmt_bridge_value(v, mode):
    """Format value with appropriate unit."""
    if mode == 'rp':
        return fmt_rp(v)
    elif mode == 'pp':
        return f"{v:+.3f}pp"
    else:  # pct
        return f"{v:+.2f}%"


def make_tornado_chart(pvm, scope='TOTAL', mode='rp'):
    """
    Horizontal tornado/diverging bar chart, sorted by impact magnitude.
    Centered at 0, positive (green) right, negative (red) left.
    """
    steps = get_bridge_steps(pvm, scope, mode)
    # Sort by absolute magnitude descending
    sorted_steps = sorted(steps.items(), key=lambda x: abs(x[1]), reverse=True)
    labels = [s[0] for s in sorted_steps]
    values = [s[1] for s in sorted_steps]
    colors = ['#059669' if v >= 0 else '#DC2626' for v in values]
    text_vals = [fmt_bridge_value(v, mode) for v in values]

    # Reverse so largest is on top
    labels = labels[::-1]
    values = values[::-1]
    colors = colors[::-1]
    text_vals = text_vals[::-1]

    unit_label = {'rp': 'Rupiah', 'pp': 'Margin pp', 'pct': 'GP Growth %'}[mode]

    fig = go.Figure(go.Bar(
        x=values,
        y=labels,
        orientation='h',
        marker_color=colors,
        text=text_vals,
        textposition='outside',
        cliponaxis=False,
    ))

    # Total summary for title
    d = pvm[scope]
    if mode == 'rp':
        total_str = fmt_rp(d['gp_end'] - d['gp_start'])
        existing = d['cogs_rp'] + d['price_rp'] + d['volmix_rp']
        existing_str = fmt_rp(existing)
    elif mode == 'pp':
        total_str = f"{d['pp_total']*100:+.3f}pp"
        existing = (d['pp_cogs'] + d['pp_price'] + d['pp_volmix']) * 100
        existing_str = f"{existing:+.3f}pp"
    else:
        gp_p1 = d['gp_start'] if d['gp_start'] else 1
        total_str = f"{(d['gp_end']-d['gp_start'])/gp_p1*100:+.2f}%"
        existing = (d['cogs_rp'] + d['price_rp'] + d['volmix_rp']) / gp_p1 * 100
        existing_str = f"{existing:+.2f}%"

    fig.update_layout(
        title=f"Tornado — {scope} ({unit_label})  |  Total: {total_str}  |  2. Existing SKU Effect: {existing_str}",
        showlegend=False,
        height=420,
        margin=dict(l=20, r=80, t=60, b=40),
        xaxis_title=unit_label,
        plot_bgcolor='white',
        bargap=0.35,
    )
    fig.update_xaxes(showgrid=True, gridcolor='#F3F4F6', zeroline=True, zerolinecolor='#9CA3AF', zerolinewidth=2)
    fig.update_yaxes(showgrid=False)
    return fig


def build_margin_pp_bridge_df(pvm, mode='pp'):
    """
    Tabel 1B style Sheet 2 — Margin Bridge per BL.
    mode:
      - 'pp' (default): Margin pp per BL. Start/End rows show absolute margin %.
      - 'rp': Rupiah. Start/End rows show GP P1 / GP P2 (Rupiah). Effect rows show Rp.
      - 'pct': Growth %. Start/End rows show '—' (no growth concept for absolute baseline)
               and add 'GP P1 → P2' summary; effect rows show step_Rp / GP_P1 × 100%.
    """
    bls = ['Dry', 'Fresh', 'Frozen', 'PL', 'TOTAL']
    rows = []

    if mode == 'pp':
        rows.append(['Margin P1 — Start (all SKU)'] +
                    [pvm[bl]['m_base'] * 100 for bl in bls] +
                    ['GV P1 all'])
        rows.append(['1. Churned SKU Effect'] +
                    [pvm[bl]['pp_B'] * 100 for bl in bls] +
                    ['GV existing P1'])
        rows.append(['2. Existing SKU Effect'] +
                    [(pvm[bl]['pp_cogs'] + pvm[bl]['pp_price'] + pvm[bl]['pp_volmix']) * 100 for bl in bls] +
                    ['Sum of 2.1+2.2+2.3'])
        rows.append(['  2.1 COGS Effect'] +
                    [pvm[bl]['pp_cogs'] * 100 for bl in bls] +
                    ['GV_hyp1 = q1×p1'])
        rows.append(['  2.2 Price Effect'] +
                    [pvm[bl]['pp_price'] * 100 for bl in bls] +
                    ['GV_hyp2 = q1×p2'])
        rows.append(['  2.3 Vol/Mix Effect'] +
                    [pvm[bl]['pp_volmix'] * 100 for bl in bls] +
                    ['GV actual existing P2'])
        rows.append(['3. New SKU Effect'] +
                    [pvm[bl]['pp_G'] * 100 for bl in bls] +
                    ['GV P2 all'])
        rows.append(['Total Margin Change'] +
                    [pvm[bl]['pp_total'] * 100 for bl in bls] +
                    ['End - Start'])
        rows.append(['Margin P2 — End (all SKU)'] +
                    [pvm[bl]['m_end'] * 100 for bl in bls] +
                    ['GV P2 all'])
    elif mode == 'rp':
        rows.append(['GP P1 — Start (all SKU)'] +
                    [pvm[bl]['gp_start'] for bl in bls] +
                    ['GP P1 all'])
        rows.append(['1. Churned SKU Effect'] +
                    [-pvm[bl]['gp_dep'] for bl in bls] +
                    ['Removed SKU P1 GP'])
        rows.append(['2. Existing SKU Effect'] +
                    [pvm[bl]['cogs_rp'] + pvm[bl]['price_rp'] + pvm[bl]['volmix_rp'] for bl in bls] +
                    ['Sum of 2.1+2.2+2.3'])
        rows.append(['  2.1 COGS Effect'] +
                    [pvm[bl]['cogs_rp'] for bl in bls] +
                    ['q1 × (c1 - c2)'])
        rows.append(['  2.2 Price Effect'] +
                    [pvm[bl]['price_rp'] for bl in bls] +
                    ['q1 × (p2 - p1)'])
        rows.append(['  2.3 Vol/Mix Effect'] +
                    [pvm[bl]['volmix_rp'] for bl in bls] +
                    ['(q2-q1) × (p2-c2)'])
        rows.append(['3. New SKU Effect'] +
                    [pvm[bl]['gp_new'] for bl in bls] +
                    ['New SKU P2 GP'])
        rows.append(['Total GP Change'] +
                    [pvm[bl]['gp_end'] - pvm[bl]['gp_start'] for bl in bls] +
                    ['End - Start'])
        rows.append(['GP P2 — End (all SKU)'] +
                    [pvm[bl]['gp_end'] for bl in bls] +
                    ['GP P2 all'])
    else:  # pct (growth %)
        def safe_div(num, den):
            return num / den * 100 if den else 0

        rows.append(['GP P1 — Start (all SKU)'] +
                    [pvm[bl]['gp_start'] for bl in bls] +
                    ['Baseline GP P1'])
        rows.append(['1. Churned SKU Effect'] +
                    [safe_div(-pvm[bl]['gp_dep'], pvm[bl]['gp_start']) for bl in bls] +
                    ['as % of GP P1'])
        rows.append(['2. Existing SKU Effect'] +
                    [safe_div(pvm[bl]['cogs_rp'] + pvm[bl]['price_rp'] + pvm[bl]['volmix_rp'],
                             pvm[bl]['gp_start']) for bl in bls] +
                    ['as % of GP P1'])
        rows.append(['  2.1 COGS Effect'] +
                    [safe_div(pvm[bl]['cogs_rp'], pvm[bl]['gp_start']) for bl in bls] +
                    ['as % of GP P1'])
        rows.append(['  2.2 Price Effect'] +
                    [safe_div(pvm[bl]['price_rp'], pvm[bl]['gp_start']) for bl in bls] +
                    ['as % of GP P1'])
        rows.append(['  2.3 Vol/Mix Effect'] +
                    [safe_div(pvm[bl]['volmix_rp'], pvm[bl]['gp_start']) for bl in bls] +
                    ['as % of GP P1'])
        rows.append(['3. New SKU Effect'] +
                    [safe_div(pvm[bl]['gp_new'], pvm[bl]['gp_start']) for bl in bls] +
                    ['as % of GP P1'])
        rows.append(['Total GP Growth %'] +
                    [safe_div(pvm[bl]['gp_end'] - pvm[bl]['gp_start'], pvm[bl]['gp_start']) for bl in bls] +
                    ['(End - Start) / Start'])
        rows.append(['GP P2 — End (all SKU)'] +
                    [pvm[bl]['gp_end'] for bl in bls] +
                    ['Ending GP P2'])

    cols = ['Step', 'Dry', 'Fresh', 'Frozen', 'PL', 'Overall', 'Reference']
    return pd.DataFrame(rows, columns=cols)


def build_bl_contribution_df(pvm):
    """
    Tabel 2 — BL Contribution to Overall margin change.
    Methodology (matches Sheet 2 Tabel 3 in pvm_analyzer_v3.py):
      Per-effect contribution per BL = pp_step_BL × GV_weight_P2_BL
      Σ Margin Change (via components) = sum of per-effect contributions
      Margin Change Effect (direct) = ΔMargin_BL × GV_weight_P2_BL
      Residual = (Σ via components) - (direct) ≈ 0
      BL Mix Effect = ΔWeight_BL × Margin_P1_BL
      Total Overall = Margin Change (direct) + BL Mix Effect = Actual Overall ΔMargin (exact identity)

    Rows: 1. Churned, 2. Existing (sum), 2.1 COGS, 2.2 Price, 2.3 Vol/Mix, 3. New SKU,
          Σ Margin Change Effect (via components), Margin Change Effect (direct),
          Residual (via - direct), BL Mix Effect, Total Overall.
    Cols: Dry contrib, Fresh contrib, Frozen contrib, PL contrib, Overall.
    """
    bls = ['Dry', 'Fresh', 'Frozen', 'PL']
    total_gv_p1 = sum(pvm[bl]['gv_start'] for bl in bls)
    total_gv_p2 = sum(pvm[bl]['gv_end'] for bl in bls)
    weights_p1 = {bl: pvm[bl]['gv_start'] / total_gv_p1 if total_gv_p1 else 0 for bl in bls}
    weights_p2 = {bl: pvm[bl]['gv_end'] / total_gv_p2 if total_gv_p2 else 0 for bl in bls}

    rows = []
    steps = [
        ('1. Churned SKU Effect', 'pp_B'),
        ('2. Existing SKU Effect', '__existing__'),
        ('  2.1 COGS Effect', 'pp_cogs'),
        ('  2.2 Price Effect', 'pp_price'),
        ('  2.3 Vol/Mix Effect', 'pp_volmix'),
        ('3. New SKU Effect', 'pp_G'),
    ]
    # Per-effect contribution rows
    for label, key in steps:
        row = [label]
        for bl in bls:
            if key == '__existing__':
                bl_pp = pvm[bl]['pp_cogs'] + pvm[bl]['pp_price'] + pvm[bl]['pp_volmix']
            else:
                bl_pp = pvm[bl][key]
            contrib = bl_pp * weights_p2[bl] * 100
            row.append(contrib)
        row.append(sum(row[1:]))  # Overall = sum
        rows.append(row)

    # Σ Margin Change Effect (via components) = sum of 1.Churned + 2.Existing + 3.New per BL
    sum_within_row = ['Σ Margin Change Effect (via components)']
    for bl in bls:
        v = (pvm[bl]['pp_B'] + pvm[bl]['pp_cogs'] + pvm[bl]['pp_price']
             + pvm[bl]['pp_volmix'] + pvm[bl]['pp_G']) * weights_p2[bl] * 100
        sum_within_row.append(v)
    sum_within_row.append(sum(sum_within_row[1:]))
    rows.append(sum_within_row)

    # Margin Change Effect (direct) = ΔMargin_BL × weight_P2_BL
    direct_row = ['Margin Change Effect (direct)']
    for bl in bls:
        v = pvm[bl]['pp_total'] * weights_p2[bl] * 100
        direct_row.append(v)
    direct_row.append(sum(direct_row[1:]))
    rows.append(direct_row)

    # Residual = via - direct (should be ~0)
    residual_row = ['Residual (via comp - direct)']
    for i, bl in enumerate(bls, 1):
        residual_row.append(sum_within_row[i] - direct_row[i])
    residual_row.append(sum(residual_row[1:]))
    rows.append(residual_row)

    # BL Mix Effect = ΔWeight_BL × Margin_P1_BL
    blmix_row = ['BL Mix Effect']
    for bl in bls:
        delta_w = weights_p2[bl] - weights_p1[bl]
        m_p1 = pvm[bl]['m_base']
        v = delta_w * m_p1 * 100
        blmix_row.append(v)
    blmix_row.append(sum(blmix_row[1:]))
    rows.append(blmix_row)

    # Total Overall = Margin Change (direct) + BL Mix
    total_row = ['Total Overall']
    for i in range(1, 5):  # per BL: leave blank as concept doesn't apply per-BL
        total_row.append(None)
    total_row.append(direct_row[5] + blmix_row[5])
    rows.append(total_row)

    cols = ['Step', 'Dry contrib', 'Fresh contrib', 'Frozen contrib', 'PL contrib', 'Overall']
    return pd.DataFrame(rows, columns=cols)



def compute_l1_breakdown(df):
    """Aggregate GP P1, GP P2, GP Diff per L1 category."""
    g = df.groupby(['pricing_bl', 'l1_category'], dropna=False).agg(
        gp_p1=('gp_p1', 'sum'),
        gp_p2=('gp_p2', 'sum'),
        gv_p1=('gv_p1', 'sum'),
        gv_p2=('gv_p2', 'sum'),
        qty_p1=('qty_p1', 'sum'),
        qty_p2=('qty_p2', 'sum'),
        n_sku=('product_id', 'nunique') if 'product_id' in df.columns else ('gp_p1', 'count'),
    ).reset_index()
    g['gp_diff'] = g['gp_p2'] - g['gp_p1']
    g['gp_diff_pct'] = np.where(g['gp_p1'] != 0, g['gp_diff'] / g['gp_p1'], np.nan)
    g['margin_p1'] = np.where(g['gv_p1'] != 0, g['gp_p1'] / g['gv_p1'], np.nan)
    g['margin_p2'] = np.where(g['gv_p2'] != 0, g['gp_p2'] / g['gv_p2'], np.nan)
    g['margin_diff'] = g['margin_p2'] - g['margin_p1']
    g = g.sort_values('gp_diff', ascending=False).reset_index(drop=True)
    return g


def compute_l1_pvm(df, scope='TOTAL'):
    """
    Compute PVM decomposition per L1 category, optionally filtered by BL scope.
    Returns dict of L1 -> {effect components}.
    Components per L1:
      gp_dep, cogs_rp, price_rp, volmix_rp, gp_new, gp_start, gp_end
      m_base, m_end, pp_B, pp_cogs, pp_price, pp_volmix, pp_G, pp_total
    """
    if scope != 'TOTAL':
        df_scope = df[df['pricing_bl'] == scope].copy()
    else:
        df_scope = df.copy()

    if 'l1_category' not in df_scope.columns:
        return {}

    l1_data = {}
    for l1, g in df_scope.groupby('l1_category', dropna=False):
        if pd.isna(l1):
            continue

        # Split by status
        if 'sku_status' in g.columns:
            ex = g[g['sku_status'] == 'Existing']
            new = g[g['sku_status'] == 'New']
            dep = g[g['sku_status'] == 'Deprecated']
        else:
            ex = g; new = g.iloc[0:0]; dep = g.iloc[0:0]

        # Aggregates
        gv_ex1 = ex['gv_p1'].sum()
        gv_ex2 = ex['gv_p2'].sum()
        gp_ex1 = ex['gp_p1'].sum()
        gp_ex2 = ex['gp_p2'].sum()
        gv_dep = dep['gv_p1'].sum()
        gp_dep_val = dep['gp_p1'].sum()
        gv_new_val = new['gv_p2'].sum()
        gp_new_val = new['gp_p2'].sum()

        gp_start = gp_ex1 + gp_dep_val
        gp_end = gp_ex2 + gp_new_val
        gv_start = gv_ex1 + gv_dep
        gv_end = gv_ex2 + gv_new_val

        # Existing-only PVM
        q1 = ex['qty_p1'].fillna(0)
        q2 = ex['qty_p2'].fillna(0)
        p1 = ex['price_p1'].fillna(0)
        p2 = ex['price_p2'].fillna(0)
        c1 = ex['cogs_p1'].fillna(0)
        c2 = ex['cogs_p2'].fillna(0)

        cogs_rp = (q1 * (c1 - c2)).sum()
        price_rp = (q1 * (p2 - p1)).sum()
        volmix_rp = ((q2 - q1) * (p2 - c2)).sum()

        # Margin pp decomposition (vs gv_ex_p1 for COGS/Price, vs gv_ex_p2 for Vol/Mix)
        m_base = gp_start / gv_start if gv_start else 0
        m_end = gp_end / gv_end if gv_end else 0
        m_ex1 = gp_ex1 / gv_ex1 if gv_ex1 else 0
        m_ex2 = gp_ex2 / gv_ex2 if gv_ex2 else 0
        gp_h1 = gv_ex1 - (q1 * c2).sum() if gv_ex1 else 0
        gp_h2 = (q1 * p2).sum() - (q1 * c2).sum() if gv_ex1 else 0
        gv_h2 = (q1 * p2).sum()
        m_h1 = gp_h1 / gv_ex1 if gv_ex1 else 0
        m_h2 = gp_h2 / gv_h2 if gv_h2 else 0

        pp_B = m_ex1 - m_base
        pp_cogs = m_h1 - m_ex1
        pp_price = m_h2 - m_h1
        pp_volmix = m_ex2 - m_h2
        pp_G = m_end - m_ex2

        l1_data[l1] = {
            'pricing_bl': g['pricing_bl'].iloc[0] if 'pricing_bl' in g.columns else None,
            'gv_start': gv_start, 'gv_end': gv_end,
            'gp_start': gp_start, 'gp_end': gp_end,
            'gp_dep': gp_dep_val, 'gp_new': gp_new_val,
            'cogs_rp': cogs_rp, 'price_rp': price_rp, 'volmix_rp': volmix_rp,
            'm_base': m_base, 'm_end': m_end,
            'pp_B': pp_B, 'pp_cogs': pp_cogs, 'pp_price': pp_price,
            'pp_volmix': pp_volmix, 'pp_G': pp_G,
            'pp_total': pp_B + pp_cogs + pp_price + pp_volmix + pp_G,
        }
    return l1_data


def build_l1_decomp_df(df, scope='TOTAL', mode='rp'):
    """
    Tabel L1 PVM Decomposition — L1 effect breakdown per scope, dengan kolom kontekstual.

    Layout per mode:
      - 'rp': L1 | BL | GP P1 | GV Weight P1 | [effects in Rp] | Total Δ | GP P2 | GV Weight P2
      - 'pct': L1 | BL | GP P1 | GV Weight P1 | [effects in growth%] | Total Δ | GP P2 | GV Weight P2
      - 'pp': L1 | BL | Margin P1 | GV Weight P1 | [effects in pp within L1] | Total Δ | Margin P2 | GV Weight P2
      - 'pp_contrib': L1 | BL | Margin P1 | GV Weight P1 | [effects in pp×weight] | Margin Change Effect | GV Weight Effect | Total Δ | Margin P2 | GV Weight P2

    GV Weight = L1_GV / scope_total_GV (terhadap scope yang dipilih).

    Math identity untuk pp_contrib mode:
      Margin Change Effect_L1 = pp_total_L1 × weight_P2_L1_in_scope
      GV Weight Effect_L1 = ΔWeight_L1_in_scope × Margin_P1_L1
      Total Δ_L1 = Margin Change + GV Weight
      Σ across L1 in scope = scope's actual ΔMargin (exact)
    """
    l1_data = compute_l1_pvm(df, scope=scope)
    if not l1_data:
        return pd.DataFrame()

    # Scope-level GV totals (for weighting)
    total_gv_p1 = sum(d['gv_start'] for d in l1_data.values())
    total_gv_p2 = sum(d['gv_end'] for d in l1_data.values())

    rows = []
    for l1, d in l1_data.items():
        bl = d['pricing_bl']
        w_p1 = d['gv_start'] / total_gv_p1 if total_gv_p1 else 0
        w_p2 = d['gv_end'] / total_gv_p2 if total_gv_p2 else 0

        if mode == 'rp':
            row = {
                'L1 Category': l1, 'BL': bl,
                'GP P1': d['gp_start'],
                'GV Weight P1': w_p1,
                '1. Churned': -d['gp_dep'],
                '2. Existing': d['cogs_rp'] + d['price_rp'] + d['volmix_rp'],
                '  2.1 COGS': d['cogs_rp'],
                '  2.2 Price': d['price_rp'],
                '  2.3 Vol/Mix': d['volmix_rp'],
                '3. New': d['gp_new'],
                'Total Δ': d['gp_end'] - d['gp_start'],
                'GP P2': d['gp_end'],
                'GV Weight P2': w_p2,
            }
        elif mode == 'pct':
            gp1 = d['gp_start'] if d['gp_start'] else 1
            row = {
                'L1 Category': l1, 'BL': bl,
                'GP P1': d['gp_start'],
                'GV Weight P1': w_p1,
                '1. Churned': (-d['gp_dep']) / gp1 * 100,
                '2. Existing': (d['cogs_rp'] + d['price_rp'] + d['volmix_rp']) / gp1 * 100,
                '  2.1 COGS': d['cogs_rp'] / gp1 * 100,
                '  2.2 Price': d['price_rp'] / gp1 * 100,
                '  2.3 Vol/Mix': d['volmix_rp'] / gp1 * 100,
                '3. New': d['gp_new'] / gp1 * 100,
                'Total Δ': (d['gp_end'] - d['gp_start']) / gp1 * 100,
                'GP P2': d['gp_end'],
                'GV Weight P2': w_p2,
            }
        elif mode == 'pp':
            row = {
                'L1 Category': l1, 'BL': bl,
                'Margin P1': d['m_base'] * 100,
                'GV Weight P1': w_p1,
                '1. Churned': d['pp_B'] * 100,
                '2. Existing': (d['pp_cogs'] + d['pp_price'] + d['pp_volmix']) * 100,
                '  2.1 COGS': d['pp_cogs'] * 100,
                '  2.2 Price': d['pp_price'] * 100,
                '  2.3 Vol/Mix': d['pp_volmix'] * 100,
                '3. New': d['pp_G'] * 100,
                'Total Δ': d['pp_total'] * 100,
                'Margin P2': d['m_end'] * 100,
                'GV Weight P2': w_p2,
            }
        else:  # pp_contrib
            delta_w = w_p2 - w_p1
            churned_c = d['pp_B'] * w_p2 * 100
            cogs_c = d['pp_cogs'] * w_p2 * 100
            price_c = d['pp_price'] * w_p2 * 100
            volmix_c = d['pp_volmix'] * w_p2 * 100
            new_c = d['pp_G'] * w_p2 * 100
            existing_c = cogs_c + price_c + volmix_c
            margin_change_total = churned_c + existing_c + new_c  # = pp_total × w_p2 × 100
            gv_weight_effect = delta_w * d['m_base'] * 100
            row = {
                'L1 Category': l1, 'BL': bl,
                'Margin P1': d['m_base'] * 100,
                'GV Weight P1': w_p1,
                '1. Churned': churned_c,
                '2. Existing': existing_c,
                '  2.1 COGS': cogs_c,
                '  2.2 Price': price_c,
                '  2.3 Vol/Mix': volmix_c,
                '3. New': new_c,
                'Margin Change Effect': margin_change_total,
                'GV Weight Effect': gv_weight_effect,
                'Total Δ': margin_change_total + gv_weight_effect,
                'Margin P2': d['m_end'] * 100,
                'GV Weight P2': w_p2,
            }
        rows.append(row)

    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values('Total Δ', ascending=False).reset_index(drop=True)
    return out


def build_l1_overall_row(df, scope, mode, pvm):
    """
    Build single 'Overall' row for Tabel L1 (placed at bottom).

    Sum-able modes (rp, pp_contrib):
      Row Overall = sum of all L1 (column-wise sum) — exact match with scope's actual total

    Non-sum-able modes (pct, pp):
      Row Overall = scope-level aggregate (compute fresh, NOT sum of L1)
      Reason: growth%/margin pp are non-linear (denominator-dependent), sum-of-L1 != scope-level
    """
    scope_data = pvm.get(scope) if scope != 'TOTAL' else pvm.get('TOTAL')
    if not scope_data:
        return None

    if mode in ('rp', 'pp_contrib'):
        # Sum-able: compute fresh from compute_l1_pvm and sum columns
        ldf = build_l1_decomp_df(df, scope=scope, mode=mode)
        if ldf.empty:
            return None
        overall = {'L1 Category': 'OVERALL (Sum L1)', 'BL': '—'}
        for col in ldf.columns:
            if col in ('L1 Category', 'BL'): continue
            if col in ('GV Weight P1', 'GV Weight P2'):
                overall[col] = 1.0  # 100% by definition of scope
            elif col in ('GP P1', 'GP P2', 'Margin P1', 'Margin P2'):
                # Show scope-level absolute baseline
                if col == 'GP P1':
                    overall[col] = scope_data['gp_start']
                elif col == 'GP P2':
                    overall[col] = scope_data['gp_end']
                elif col == 'Margin P1':
                    overall[col] = scope_data['m_base'] * 100
                elif col == 'Margin P2':
                    overall[col] = scope_data['m_end'] * 100
            else:
                overall[col] = ldf[col].sum()
        return overall
    else:  # pct, pp — non-sum-able, compute scope-level fresh
        d = scope_data
        if mode == 'pct':
            gp1 = d['gp_start'] if d['gp_start'] else 1
            existing_rp = d['cogs_rp'] + d['price_rp'] + d['volmix_rp']
            return {
                'L1 Category': 'OVERALL (Scope-level)', 'BL': '—',
                'GP P1': d['gp_start'],
                'GV Weight P1': 1.0,
                '1. Churned': (-d['gp_dep']) / gp1 * 100,
                '2. Existing': existing_rp / gp1 * 100,
                '  2.1 COGS': d['cogs_rp'] / gp1 * 100,
                '  2.2 Price': d['price_rp'] / gp1 * 100,
                '  2.3 Vol/Mix': d['volmix_rp'] / gp1 * 100,
                '3. New': d['gp_new'] / gp1 * 100,
                'Total Δ': (d['gp_end'] - d['gp_start']) / gp1 * 100,
                'GP P2': d['gp_end'],
                'GV Weight P2': 1.0,
            }
        else:  # pp (within L1)
            return {
                'L1 Category': 'OVERALL (Scope-level)', 'BL': '—',
                'Margin P1': d['m_base'] * 100,
                'GV Weight P1': 1.0,
                '1. Churned': d['pp_B'] * 100,
                '2. Existing': (d['pp_cogs'] + d['pp_price'] + d['pp_volmix']) * 100,
                '  2.1 COGS': d['pp_cogs'] * 100,
                '  2.2 Price': d['pp_price'] * 100,
                '  2.3 Vol/Mix': d['pp_volmix'] * 100,
                '3. New': d['pp_G'] * 100,
                'Total Δ': d['pp_total'] * 100,
                'Margin P2': d['m_end'] * 100,
                'GV Weight P2': 1.0,
            }



def _enrich_existing_with_effects(df):
    """
    Filter to Existing SKU only and add per-SKU decomposition + Δ Rp columns.
    Returns enriched DataFrame.
    """
    if 'sku_status' in df.columns:
        existing = df[df['sku_status'] == 'Existing'].copy()
    else:
        existing = df.copy()
    existing = existing.dropna(subset=['gp_diff'])

    # Per-SKU PVM decomposition
    # COGS Effect_sku = q_p1 × (cogs_p1 - cogs_p2)   ← positive = COGS turun = bantu GP
    # Price Effect_sku = q_p1 × (price_p2 - price_p1) ← positive = Price naik = bantu GP
    # Vol/Mix Effect_sku = (q_p2 - q_p1) × (price_p2 - cogs_p2)  ← positive = qty naik
    q1 = existing['qty_p1'].fillna(0)
    q2 = existing['qty_p2'].fillna(0)
    p1 = existing['price_p1'].fillna(0)
    p2 = existing['price_p2'].fillna(0)
    c1 = existing['cogs_p1'].fillna(0)
    c2 = existing['cogs_p2'].fillna(0)

    existing['cogs_effect'] = q1 * (c1 - c2)
    existing['price_effect'] = q1 * (p2 - p1)
    existing['volmix_effect'] = (q2 - q1) * (p2 - c2)

    # Δ Rp (nominal per-unit changes)
    existing['price_diff_rp'] = p2 - p1
    existing['cogs_diff_rp'] = c2 - c1

    # Per-SKU margin P1, P2 (unit margin)
    existing['margin_p1_pct'] = np.where(p1 > 0, (p1 - c1) / p1 * 100, np.nan)
    existing['margin_p2_pct'] = np.where(p2 > 0, (p2 - c2) / p2 * 100, np.nan)

    # Avg stock P1, P2 + growth %
    if 'avg_stock_p1' in existing.columns and 'avg_stock_p2' in existing.columns:
        s1 = existing['avg_stock_p1']
        s2 = existing['avg_stock_p2']
        existing['avg_stock_growth_pct'] = np.where(s1 > 0, (s2 - s1) / s1 * 100, np.nan)
    else:
        existing['avg_stock_p1'] = np.nan
        existing['avg_stock_p2'] = np.nan
        existing['avg_stock_growth_pct'] = np.nan

    # Growth % = sku_gp_diff / sku_gp_p1 (per-SKU growth)
    gp1 = existing['gp_p1'].replace(0, np.nan)
    existing['gp_growth_pct'] = (existing['gp_diff'] / gp1) * 100

    return existing


def compute_top_movers_gp(df, n=10):
    """Top n by GP Δ — gainers (highest gp_diff) and losers (lowest)."""
    existing = _enrich_existing_with_effects(df)
    gainers = existing.nlargest(n, 'gp_diff')
    losers = existing.nsmallest(n, 'gp_diff')
    return gainers, losers


def compute_top_movers_price(df, n=10):
    """Top n by Price Δ% — up (highest) and down (lowest)."""
    existing = _enrich_existing_with_effects(df)
    existing = existing.dropna(subset=['price_diff_pct'])
    ups = existing.nlargest(n, 'price_diff_pct')
    downs = existing.nsmallest(n, 'price_diff_pct')
    return ups, downs


def compute_top_movers_cogs(df, n=10):
    """Top n by COGS Δ% — up (highest) and down (lowest)."""
    existing = _enrich_existing_with_effects(df)
    existing = existing.dropna(subset=['cogs_diff_pct'])
    ups = existing.nlargest(n, 'cogs_diff_pct')
    downs = existing.nsmallest(n, 'cogs_diff_pct')
    return ups, downs


def compute_top_movers(df, n=10):
    """Backward compat alias for GP movers."""
    return compute_top_movers_gp(df, n)

def compute_watch_priority(df):
    """Find Priority SKUs: (Up,Up,Flat) or (Drop,Drop,Flat) on (cogs, comp, price)."""
    if 'flag_price' in df.columns:
        return df[df['flag_price'] == 'Priority'].copy()
    # Fallback: compute from status cols
    priority_mask = (
        ((df.get('cogs_status') == 'Up') & (df.get('comp_status') == 'Up') & (df.get('price_status') == 'Flat')) |
        ((df.get('cogs_status') == 'Drop') & (df.get('comp_status') == 'Drop') & (df.get('price_status') == 'Flat'))
    )
    return df[priority_mask].copy()

def make_template_excel():
    """Generate a downloadable template Excel with required cols and 2 sample rows."""
    template = pd.DataFrame({
        'week_key': ['2026-05-04', '2026-05-04'],
        'next_week': ['2026-05-11', '2026-05-11'],
        'product_id': ['SKU001', 'SKU002'],
        'product_name': ['Sample Product A', 'Sample Product B'],
        'pricing_bl_25': ['Dry', 'Fresh'],
        'l1_category_name': ['Beverages', 'Dairy & Eggs'],
        'business_lines_2025': ['Dry', 'Fresh'],
        'pareto_classification': ['A', 'B'],
        'selling_price': [10000, 25000],
        'selling_price1': [10500, 25000],
        'cost_price': [7000, 18000],
        'cost_price1': [7100, 17500],
        'qty': [120, 80],
        'qty1': [130, 75],
        'comp_price': [10200, 24500],
        'comp_price1': [10300, 24800],
        'pi': [98.04, 102.04],
        'pi1': [101.94, 100.81],
        'avg_stock': [200, 150],
        'avg_stock1': [180, 160],
    })
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        template.to_excel(writer, sheet_name='Sheet1', index=False)
    buf.seek(0)
    return buf.getvalue()

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
if 'pvm_analysis' not in st.session_state:
    st.session_state.pvm_analysis = None
if 'pvm_uploaded_file_name' not in st.session_state:
    st.session_state.pvm_uploaded_file_name = None
if 'pvm_uploaded_file_size' not in st.session_state:
    st.session_state.pvm_uploaded_file_size = None

# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────
col_title, col_clear = st.columns([5, 1])
with col_title:
    st.title("📊 PVM Analyzer")
    st.caption("Pricing × Volume × Mix Decomposition — Astro Pricing Strategy")
with col_clear:
    st.write("")
    if st.session_state.pvm_analysis is not None:
        if st.button("🗑️ Clear data", type="secondary", use_container_width=True):
            st.session_state.pvm_analysis = None
            st.session_state.pvm_uploaded_file_name = None
            st.session_state.pvm_uploaded_file_size = None
            st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# ZONE 1 — UPLOAD
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">📁 Upload Data</div>', unsafe_allow_html=True)

up_col1, up_col2 = st.columns([3, 1])
with up_col1:
    uploaded = st.file_uploader(
        "Upload file Excel atau CSV (raw input per-SKU per-periode)",
        type=['xlsx', 'xls', 'csv'],
        help="Format mengikuti pvm_analyzer_v3.py: butuh kolom selling_price, cost_price, qty (P1 & P2)",
    )
with up_col2:
    st.write("")
    st.write("")
    template_bytes = make_template_excel()
    st.download_button(
        "📥 Download Template",
        data=template_bytes,
        file_name="pvm_template.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        help="Download template Excel kosong dengan format kolom yang benar"
    )

# ─────────────────────────────────────────────────────────────────────────────
# PROCESS UPLOAD
# ─────────────────────────────────────────────────────────────────────────────
file_changed = (
    uploaded is not None and
    (st.session_state.pvm_uploaded_file_name != uploaded.name or
     st.session_state.pvm_uploaded_file_size != uploaded.size or
     st.session_state.pvm_analysis is None)
)
if file_changed:
    # Load file
    try:
        if uploaded.name.lower().endswith('.csv'):
            df_input = pd.read_csv(uploaded)
        else:
            df_input = pd.read_excel(uploaded)
    except Exception as e:
        st.error(f"❌ Gagal load file: {e}")
        st.stop()

    # Validation panel
    st.markdown("### ✅ Validation")
    cols_in = list(df_input.columns)

    val_col1, val_col2 = st.columns(2)
    with val_col1:
        st.markdown(f"**File:** `{uploaded.name}`")
        st.markdown(f"**Rows:** {len(df_input):,}")
        st.markdown(f"**Cols:** {len(cols_in)}")

        # Period detection
        period_pair = None
        for p1c, p2c in PERIOD_PAIRS:
            if p1c in cols_in and p2c in cols_in:
                period_pair = (p1c, p2c)
                break
        if period_pair:
            try:
                p1_val = str(df_input[period_pair[0]].dropna().iloc[0])[:10]
                p2_val = str(df_input[period_pair[1]].dropna().iloc[0])[:10]
                st.success(f"✅ Period detected: `{period_pair[0]}` ({p1_val}) vs `{period_pair[1]}` ({p2_val})")
            except Exception:
                st.warning(f"⚠️ Period cols ada tapi nilai tidak terbaca")
        else:
            st.warning("⚠️ Period cols tidak ditemukan. Akan pakai default `P1` vs `P2`.")

    with val_col2:
        # Required cols
        missing_required = [c for c in REQUIRED_COLS if c not in cols_in]
        if not missing_required:
            st.success(f"✅ Required cols complete: {', '.join(REQUIRED_COLS)}")
        else:
            st.error(f"❌ MISSING required cols: {', '.join(missing_required)}")

        # Optional cols
        missing_opt = [c for c in OPTIONAL_COLS if c not in cols_in]
        present_opt = [c for c in OPTIONAL_COLS if c in cols_in]
        if missing_opt:
            st.warning(f"⚠️ Optional cols hilang: {', '.join(missing_opt)} → akan diisi NaN")
        if present_opt:
            st.info(f"ℹ️ Optional cols ada: {', '.join(present_opt)}")

        # Dimension cols
        missing_dim = [c for c in DIM_COLS if c not in cols_in]
        if missing_dim:
            st.warning(f"⚠️ Dimension cols hilang: {', '.join(missing_dim)} → BL/L1 analysis tidak akurat")

    # Preview
    with st.expander("👀 Preview top 5 rows", expanded=False):
        st.dataframe(df_input.head(5), use_container_width=True)

    # Block if missing required
    if missing_required:
        st.error("Tidak bisa lanjut. Kolom wajib hilang. Cek format sesuai template.")
        st.stop()

    # Process
    if st.button("🚀 Process Data", type="primary", use_container_width=False):
        with st.spinner("Processing... (mungkin 10-30 detik untuk file besar)"):
            try:
                result = analyze(df_input, progress_callback=lambda m, c, t: None)
                st.session_state.pvm_analysis = result
                st.session_state.pvm_uploaded_file_name = uploaded.name
                st.session_state.pvm_uploaded_file_size = uploaded.size
                st.success(f"✅ Data processed: {result['meta']['n_rows']:,} rows enriched")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Processing error: {e}")
                import traceback
                st.code(traceback.format_exc())

# ─────────────────────────────────────────────────────────────────────────────
# ANALYSIS DISPLAY (only if data is processed)
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state.pvm_analysis is not None:
    A = st.session_state.pvm_analysis
    df = A['df']
    pvm = A['pvm']
    p1, p2 = A['p1'], A['p2']
    TOT = pvm['TOTAL']

    st.markdown(f'<div class="section-header">📈 Hasil Analisis — {p1} vs {p2}</div>', unsafe_allow_html=True)
    st.caption(f"📌 File: `{st.session_state.pvm_uploaded_file_name}` · {A['meta']['n_rows']:,} SKU diproses")

    # ─────────────────────────────────────────────────────────────────────
    # ANOMALY BANNER
    # ─────────────────────────────────────────────────────────────────────
    anomalies = detect_anomalies(pvm)
    if anomalies:
        if len(anomalies) == 1:
            a = anomalies[0]
            drivers_txt = "; ".join(a['drivers']) if a['drivers'] else "lihat detail di Margin Bridge"
            st.markdown(
                f'<div class="banner-warn">'
                f'<div class="banner-title">⚠️ {a["bl"]} flagged</div>'
                f'GP turun <b>{a["gp_pct"]*100:.1f}%</b> ({fmt_rp(a["gp_diff"])} Rp) — {drivers_txt}.'
                f'</div>',
                unsafe_allow_html=True
            )
        else:
            bl_list = ", ".join([f"{a['bl']} (GP {a['gp_pct']*100:.1f}%)" for a in anomalies])
            st.markdown(
                f'<div class="banner-warn">'
                f'<div class="banner-title">⚠️ {len(anomalies)} BL flagged</div>'
                f'{bl_list}. Lihat detail per BL di Margin Bridge & L1 Breakdown.'
                f'</div>',
                unsafe_allow_html=True
            )
    else:
        st.markdown(
            '<div class="banner-ok">'
            '<div class="banner-title">✅ Semua BL dalam threshold normal</div>'
            'Tidak ada anomaly minggu ini (GP Δ% > -3% dan GV Δ% > -4%).'
            '</div>',
            unsafe_allow_html=True
        )

    # ─────────────────────────────────────────────────────────────────────
    # ZONE 2 — EXECUTIVE KPI STRIP
    # ─────────────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">2️⃣ Executive Summary</div>', unsafe_allow_html=True)

    gv_p1, gv_p2 = TOT['gv_start'], TOT['gv_end']
    gp_p1, gp_p2 = TOT['gp_start'], TOT['gp_end']
    m_p1, m_p2 = TOT['m_base'], TOT['m_end']
    gv_diff = gv_p2 - gv_p1
    gv_diff_pct = gv_diff / gv_p1 if gv_p1 else 0
    gp_diff = gp_p2 - gp_p1
    gp_diff_pct = gp_diff / gp_p1 if gp_p1 else 0
    margin_diff = m_p2 - m_p1

    # COGS (Overall): GV - GP
    cogs_p1 = gv_p1 - gp_p1
    cogs_p2 = gv_p2 - gp_p2
    cogs_diff = cogs_p2 - cogs_p1
    cogs_diff_pct = cogs_diff / cogs_p1 if cogs_p1 else 0

    # SKU counts
    if 'sku_status' in df.columns:
        n_existing = (df['sku_status'] == 'Existing').sum()
        n_new = (df['sku_status'] == 'New').sum()
        n_dep = (df['sku_status'] == 'Deprecated').sum()
        n_active_p2 = n_existing + n_new
        n_active_p1 = n_existing + n_dep
    else:
        n_existing = n_new = n_dep = n_active_p2 = n_active_p1 = 0

    # Qty OVERALL (Definisi A): P1 = Existing+Dep, P2 = Existing+New
    if 'sku_status' in df.columns:
        qty_p1_overall = df[df['sku_status'].isin(['Existing', 'Deprecated'])]['qty_p1'].sum()
        qty_p2_overall = df[df['sku_status'].isin(['Existing', 'New'])]['qty_p2'].sum()
        qty_p1_existing = df[df['sku_status'] == 'Existing']['qty_p1'].sum()
        qty_p2_existing = df[df['sku_status'] == 'Existing']['qty_p2'].sum()
        gv_p1_existing = df[df['sku_status'] == 'Existing']['gv_p1'].sum()
        gv_p2_existing = df[df['sku_status'] == 'Existing']['gv_p2'].sum()
    else:
        qty_p1_overall = df['qty_p1'].sum()
        qty_p2_overall = df['qty_p2'].sum()
        qty_p1_existing = qty_p1_overall
        qty_p2_existing = qty_p2_overall
        gv_p1_existing = gv_p1
        gv_p2_existing = gv_p2

    qty_diff_overall = qty_p2_overall - qty_p1_overall
    qty_diff_pct_overall = qty_diff_overall / qty_p1_overall if qty_p1_overall else 0

    # Avg Price/Unit (Existing only, per user request)
    avg_price_p1 = gv_p1_existing / qty_p1_existing if qty_p1_existing else 0
    avg_price_p2 = gv_p2_existing / qty_p2_existing if qty_p2_existing else 0
    avg_price_diff = avg_price_p2 - avg_price_p1
    avg_price_diff_pct = avg_price_diff / avg_price_p1 if avg_price_p1 else 0

    # GP per SKU (productivity metric)
    gp_per_sku_p1 = gp_p1 / n_active_p1 if n_active_p1 else 0
    gp_per_sku_p2 = gp_p2 / n_active_p2 if n_active_p2 else 0
    gp_per_sku_diff = gp_per_sku_p2 - gp_per_sku_p1
    gp_per_sku_diff_pct = gp_per_sku_diff / gp_per_sku_p1 if gp_per_sku_p1 else 0

    # Row 1: GV / GP / Margin
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(kpi_card(
            "Goods Value",
            fmt_rp(gv_p2),
            delta=gv_diff_pct,
            delta_label=f"{fmt_rp(gv_diff)} ({gv_diff_pct*100:+.2f}%)",
            sub=f"P1: {fmt_rp(gv_p1)}"
        ), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi_card(
            "Gross Profit",
            fmt_rp(gp_p2),
            delta=gp_diff_pct,
            delta_label=f"{fmt_rp(gp_diff)} ({gp_diff_pct*100:+.2f}%)",
            sub=f"P1: {fmt_rp(gp_p1)}"
        ), unsafe_allow_html=True)
    with c3:
        st.markdown(kpi_card(
            "Margin",
            fmt_pct(m_p2),
            delta=margin_diff,
            delta_label=fmt_pp(margin_diff, decimals=3),
            sub=f"P1: {fmt_pct(m_p1)}"
        ), unsafe_allow_html=True)

    # Row 2: Qty (Overall) / COGS / Avg Price/Unit (Existing)
    c4, c5, c6 = st.columns(3)
    with c4:
        st.markdown(kpi_card(
            "Qty Sold (Overall)",
            f"{qty_p2_overall/1e6:.2f} M",
            delta=qty_diff_pct_overall,
            delta_label=f"{qty_diff_overall:+,.0f} ({qty_diff_pct_overall*100:+.2f}%)",
            sub=f"P1: {qty_p1_overall/1e6:.2f} M (Existing+Dep) · P2: Existing+New"
        ), unsafe_allow_html=True)
    with c5:
        st.markdown(kpi_card(
            "COGS",
            fmt_rp(cogs_p2),
            delta=cogs_diff_pct,
            delta_label=f"{fmt_rp(cogs_diff)} ({cogs_diff_pct*100:+.2f}%)",
            sub=f"P1: {fmt_rp(cogs_p1)}",
            delta_inverse=True  # lower COGS = good
        ), unsafe_allow_html=True)
    with c6:
        st.markdown(kpi_card(
            "Avg Price/Unit",
            f"Rp {avg_price_p2:,.0f}",
            delta=avg_price_diff_pct,
            delta_label=f"{avg_price_diff:+,.0f} ({avg_price_diff_pct*100:+.2f}%)",
            sub=f"P1: Rp {avg_price_p1:,.0f} · (Existing SKU only)"
        ), unsafe_allow_html=True)

    # Row 3: # SKU Active / SKU Churn / GP per SKU
    c7, c8, c9 = st.columns(3)
    with c7:
        st.markdown(kpi_card(
            "# SKU Active P2",
            f"{n_active_p2:,}",
            sub=f"Existing: {n_existing:,} · P1 Active: {n_active_p1:,}"
        ), unsafe_allow_html=True)
    with c8:
        st.markdown(kpi_card(
            "SKU Churn",
            f"+{n_new:,} / -{n_dep:,}",
            sub=f"Net: {n_new - n_dep:+,} (New − Deprecated)"
        ), unsafe_allow_html=True)
    with c9:
        st.markdown(kpi_card(
            "GP per SKU",
            fmt_rp(gp_per_sku_p2),
            delta=gp_per_sku_diff_pct,
            delta_label=f"{fmt_rp(gp_per_sku_diff)} ({gp_per_sku_diff_pct*100:+.2f}%)",
            sub=f"P1: {fmt_rp(gp_per_sku_p1)} · Productivity"
        ), unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────
    # ZONE 3 — MARGIN BRIDGE (Tornado + 2 Tables)
    # ─────────────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">3️⃣ Margin Bridge</div>', unsafe_allow_html=True)

    # Narrative
    pp_existing_tot = TOT['pp_cogs'] + TOT['pp_price'] + TOT['pp_volmix']
    pp_total = TOT['pp_total']
    gp_diff_tot = TOT['gp_end'] - TOT['gp_start']
    growth_pct_tot = gp_diff_tot / TOT['gp_start'] if TOT['gp_start'] else 0

    drivers_sorted = sorted(
        [('2.1 COGS Effect', TOT['pp_cogs']),
         ('2.2 Price Effect', TOT['pp_price']),
         ('2.3 Vol/Mix Effect', TOT['pp_volmix']),
         ('1. Churned SKU Effect', TOT['pp_B']),
         ('3. New SKU Effect', TOT['pp_G'])],
        key=lambda x: abs(x[1]), reverse=True
    )
    top_drivers = drivers_sorted[:2]
    drivers_txt = " dan ".join([f"**{n}** ({fmt_pp(v, 3)})" for n, v in top_drivers])

    direction = "naik" if pp_total >= 0 else "turun"
    st.markdown(f"""
        Margin {direction} **{fmt_pp(pp_total, 3)}** dari **{fmt_pct(m_p1)}** ke **{fmt_pct(m_p2)}**.
        GP absolut: **{fmt_rp(gp_diff_tot)}** ({growth_pct_tot*100:+.2f}% growth vs P1).
        Driver utama: {drivers_txt}.
        Existing SKU Effect = COGS + Price + Vol/Mix = **{fmt_pp(pp_existing_tot, 3)}**.
    """)

    # Scope toggle + mode toggle (3 units now)
    bx1, bx2 = st.columns([2, 1])
    with bx1:
        scope = st.radio(
            "Scope:",
            ['TOTAL', 'Dry', 'Fresh', 'Frozen', 'PL'],
            horizontal=True,
            key='bridge_scope',
        )
    with bx2:
        mode = st.radio(
            "Unit:",
            ['Rupiah (Rp)', 'Growth %', 'Margin (pp)'],
            horizontal=True,
            key='bridge_mode'
        )
        if 'Rupiah' in mode:
            mode_key = 'rp'
        elif 'Growth' in mode:
            mode_key = 'pct'
        else:
            mode_key = 'pp'

    # Tornado chart
    fig_tornado = make_tornado_chart(pvm, scope=scope, mode=mode_key)
    st.plotly_chart(fig_tornado, use_container_width=True)

    # ── TABEL 1: Margin Bridge per BL (unit-aware) ────────────────────────
    unit_label_t1 = {'rp': 'Rupiah', 'pp': 'Margin pp', 'pct': 'Growth %'}[mode_key]
    st.markdown(f"##### 📊 Tabel 1: Margin Bridge per BL ({unit_label_t1})")
    st.caption("Margin/GP **dalam** masing-masing BL (un-weighted). Ikutin unit toggle di atas. "
               "Bisa lihat before-after per BL.")

    bridge_df = build_margin_pp_bridge_df(pvm, mode=mode_key)
    bl_cols = ['Dry', 'Fresh', 'Frozen', 'PL', 'Overall']

    # Identify row types for special handling
    def _is_baseline_row(label):
        """Margin/GP P1 Start or P2 End row — show as absolute number, not delta."""
        return 'Start' in label or 'End' in label

    def _is_total_row(label):
        return 'Total' in label and 'Effect' not in label

    # Format cells per row type
    def format_bridge_df_unit(df_, mode_):
        out_rows = []
        for _, row in df_.iterrows():
            label = row['Step']
            is_baseline = _is_baseline_row(label)
            new_row = {'Step': label}
            for col in bl_cols:
                v = row[col]
                if pd.isna(v):
                    new_row[col] = '—'
                elif mode_ == 'pp':
                    if is_baseline:
                        new_row[col] = f"{v:.2f}%"
                    else:
                        new_row[col] = f"{v:+.3f}pp"
                elif mode_ == 'rp':
                    # All values are Rp (baselines + effects)
                    new_row[col] = fmt_rp(v)
                else:  # pct
                    if is_baseline:
                        # Show GP P1/P2 as Rp (absolute baseline)
                        new_row[col] = fmt_rp(v)
                    else:
                        new_row[col] = f"{v:+.2f}%"
            new_row['Reference'] = row['Reference']
            out_rows.append(new_row)
        return pd.DataFrame(out_rows)

    bridge_display = format_bridge_df_unit(bridge_df, mode_key)

    # Color scheme: gradient red-white-green by magnitude on effect cells only.
    # Baseline rows (Margin P1/P2 Start/End) → grey subtle bg.
    def style_bridge_gradient(df_orig, df_disp):
        """Apply gradient based on numeric values in df_orig (numeric), to df_disp (str cells)."""
        # Compute color matrix from numeric values
        # vmax = max absolute across all effect (non-baseline) cells
        effect_mask = df_orig['Step'].apply(lambda s: not _is_baseline_row(s))
        effect_vals = df_orig.loc[effect_mask, bl_cols].values.flatten()
        effect_vals = [v for v in effect_vals if pd.notna(v)]
        vmax = max(abs(v) for v in effect_vals) if effect_vals else 1
        if vmax == 0: vmax = 1

        def color_cell(val_numeric, is_baseline):
            if is_baseline:
                return 'background-color: #F3F4F6; font-weight: 700;'
            if pd.isna(val_numeric):
                return ''
            # Normalize to [-1, 1]
            norm = max(-1, min(1, val_numeric / vmax))
            if norm > 0:
                # Green gradient: white → light green → strong green
                alpha = norm  # 0..1
                r = int(255 - (255-22) * alpha)   # 255 → 22 (green700 #16A34A)
                g = int(255 - (255-163) * alpha)  # 255 → 163
                b = int(255 - (255-74) * alpha)   # 255 → 74
                return f'background-color: rgb({r},{g},{b}); color: #111827;'
            elif norm < 0:
                alpha = -norm
                r = int(255 - (255-220) * alpha)  # 255 → 220 (red600 #DC2626)
                g = int(255 - (255-38) * alpha)
                b = int(255 - (255-38) * alpha)
                # Strong red → white text
                text_color = '#FFFFFF' if alpha > 0.6 else '#111827'
                return f'background-color: rgb({r},{g},{b}); color: {text_color};'
            else:
                return ''

        def apply_style(row):
            label = row['Step']
            is_baseline = _is_baseline_row(label)
            is_total = _is_total_row(label)
            styles = []
            for col in df_disp.columns:
                if col == 'Step':
                    if is_total:
                        styles.append('font-weight: 700; background-color: #DBEAFE;')
                    elif is_baseline:
                        styles.append('font-weight: 700; background-color: #F3F4F6;')
                    elif label.startswith('2. Existing'):
                        styles.append('font-weight: 600;')
                    elif label.startswith('  '):
                        styles.append('padding-left: 20px;')
                    else:
                        styles.append('')
                elif col == 'Reference':
                    styles.append('color: #6B7280; font-style: italic;')
                else:
                    # Numeric column - look up original numeric value
                    orig_idx = row.name
                    val_num = df_orig.loc[orig_idx, col] if col in df_orig.columns else np.nan
                    if is_total:
                        base_style = color_cell(val_num, False) + ' font-weight: 700;'
                    elif is_baseline:
                        base_style = 'background-color: #F3F4F6; font-weight: 700;'
                    else:
                        base_style = color_cell(val_num, False)
                    styles.append(base_style)
            return styles

        return df_disp.style.apply(apply_style, axis=1)

    st.dataframe(
        style_bridge_gradient(bridge_df, bridge_display),
        use_container_width=True, hide_index=True
    )

    # ── TABEL 2: BL Contribution to Overall (fix pp, gradient) ───────────
    st.markdown("##### 📊 Tabel 2: BL Contribution to Overall Margin Change")
    st.caption("Decomposes Overall ΔMargin into **Margin Change Effect** (margin change per BL × GV weight P2) + "
               "**BL Mix Effect** (GV weight shift × Margin P1). "
               "**Math identity:** Σ Margin Change + Σ BL Mix = Total Overall = Actual ΔMargin Overall (exact). "
               "Fix pp, tidak ikut unit toggle.")

    contrib_df = build_bl_contribution_df(pvm)
    contrib_bl_cols = ['Dry contrib', 'Fresh contrib', 'Frozen contrib', 'PL contrib', 'Overall']

    # Format cells as pp
    contrib_display = contrib_df.copy()
    for col in contrib_bl_cols:
        contrib_display[col] = contrib_display[col].apply(lambda v: f"{v:+.3f}pp" if pd.notna(v) else '—')

    def style_contrib_gradient(df_orig, df_disp):
        # Compute color range from non-total rows
        non_total = df_orig['Step'].apply(lambda s: 'Total' not in s)
        vals = df_orig.loc[non_total, contrib_bl_cols].values.flatten()
        vals = [v for v in vals if pd.notna(v)]
        vmax = max(abs(v) for v in vals) if vals else 1
        if vmax == 0: vmax = 1

        def color_cell(val_numeric):
            if pd.isna(val_numeric): return ''
            norm = max(-1, min(1, val_numeric / vmax))
            if norm > 0:
                alpha = norm
                r = int(255 - (255-22) * alpha)
                g = int(255 - (255-163) * alpha)
                b = int(255 - (255-74) * alpha)
                return f'background-color: rgb({r},{g},{b}); color: #111827;'
            elif norm < 0:
                alpha = -norm
                r = int(255 - (255-220) * alpha)
                g = int(255 - (255-38) * alpha)
                b = int(255 - (255-38) * alpha)
                text_color = '#FFFFFF' if alpha > 0.6 else '#111827'
                return f'background-color: rgb({r},{g},{b}); color: {text_color};'
            return ''

        def apply_style(row):
            label = row['Step']
            is_total = 'Total' in label
            styles = []
            for col in df_disp.columns:
                if col == 'Step':
                    if is_total:
                        styles.append('font-weight: 700; background-color: #DBEAFE;')
                    elif label.startswith('2. Existing'):
                        styles.append('font-weight: 600;')
                    elif label.startswith('  '):
                        styles.append('padding-left: 20px;')
                    else:
                        styles.append('')
                else:
                    orig_idx = row.name
                    val_num = df_orig.loc[orig_idx, col] if col in df_orig.columns else np.nan
                    base = color_cell(val_num)
                    if is_total:
                        base += ' font-weight: 700;'
                    styles.append(base)
            return styles

        return df_disp.style.apply(apply_style, axis=1)

    st.dataframe(
        style_contrib_gradient(contrib_df, contrib_display),
        use_container_width=True, hide_index=True
    )

    # Per-BL contribution table below (Rp + Growth % + GV)
    with st.expander("📋 Breakdown numerical Rp (semua BL)", expanded=False):
        # Compute total GV per periode for weight calc
        total_gv_p1_all = sum(pvm[bl]['gv_start'] for bl in BL_ORDER)
        total_gv_p2_all = sum(pvm[bl]['gv_end'] for bl in BL_ORDER)

        bridge_data = []
        for bl in ['TOTAL'] + BL_ORDER:
            d = pvm[bl]
            existing_rp = d['cogs_rp'] + d['price_rp'] + d['volmix_rp']
            gp_p1_bl = d['gp_start'] if d['gp_start'] else 1

            # GV Weight = BL_GV / total_GV per periode
            if bl == 'TOTAL':
                gv_wt_p1 = 1.0
                gv_wt_p2 = 1.0
            else:
                gv_wt_p1 = d['gv_start'] / total_gv_p1_all if total_gv_p1_all else 0
                gv_wt_p2 = d['gv_end'] / total_gv_p2_all if total_gv_p2_all else 0

            bridge_data.append({
                'Scope': bl,
                'GV P1': d['gv_start'],
                'GV P2': d['gv_end'],
                'GV Weight P1': gv_wt_p1,
                'GV Weight P2': gv_wt_p2,
                'GP P1': d['gp_start'],
                'GP P2': d['gp_end'],
                'GP Δ': d['gp_end'] - d['gp_start'],
                'Growth %': (d['gp_end'] - d['gp_start']) / gp_p1_bl * 100,
                '1. Churned (Rp)': -d['gp_dep'],
                '2. Existing (Rp)': existing_rp,
                '  2.1 COGS (Rp)': d['cogs_rp'],
                '  2.2 Price (Rp)': d['price_rp'],
                '  2.3 Vol/Mix (Rp)': d['volmix_rp'],
                '3. New SKU (Rp)': d['gp_new'],
                'Margin P1': d['m_base'],
                'Margin P2': d['m_end'],
                'Margin Δ (pp)': d['pp_total'] * 100,
            })
        bdf = pd.DataFrame(bridge_data)
        st.dataframe(
            bdf.style.format({
                'GV P1': '{:,.0f}', 'GV P2': '{:,.0f}',
                'GV Weight P1': '{:.2%}', 'GV Weight P2': '{:.2%}',
                'GP P1': '{:,.0f}', 'GP P2': '{:,.0f}', 'GP Δ': '{:,.0f}',
                'Growth %': '{:+.2f}%',
                '1. Churned (Rp)': '{:,.0f}', '2. Existing (Rp)': '{:,.0f}',
                '  2.1 COGS (Rp)': '{:,.0f}', '  2.2 Price (Rp)': '{:,.0f}',
                '  2.3 Vol/Mix (Rp)': '{:,.0f}', '3. New SKU (Rp)': '{:,.0f}',
                'Margin P1': '{:.2%}', 'Margin P2': '{:.2%}', 'Margin Δ (pp)': '{:+.3f}'
            }),
            use_container_width=True, hide_index=True
        )

    # ─────────────────────────────────────────────────────────────────────
    # ZONE 4 — L1 CATEGORY BREAKDOWN
    # ─────────────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">4️⃣ L1 Category Breakdown</div>', unsafe_allow_html=True)

    if 'l1_category' not in df.columns:
        st.warning("⚠️ Kolom `l1_category` tidak tersedia — L1 breakdown di-skip.")
    else:
        l1 = compute_l1_breakdown(df)
        top_gain = l1.head(3)
        top_loss = l1.tail(3).sort_values('gp_diff')
        gain_sum = top_gain['gp_diff'].sum()
        loss_sum = top_loss['gp_diff'].sum()

        st.markdown(f"""
            Distribusi GP change per L1 category. Top 3 gainers: **{fmt_rp(gain_sum)}** ·
            Top 3 losers: **{fmt_rp(loss_sum)}** · Net top 6 movers: **{fmt_rp(gain_sum + loss_sum)}**.
        """)

        # Filter
        bl_filter = st.multiselect(
            "Filter BL:",
            ['Dry', 'Fresh', 'Frozen', 'PL'],
            default=['Dry', 'Fresh', 'Frozen', 'PL'],
            key='l1_bl_filter'
        )
        l1_filtered = l1[l1['pricing_bl'].isin(bl_filter)].copy()

        # Display
        l1_show = l1_filtered[['l1_category', 'pricing_bl', 'n_sku', 'gv_p1', 'gv_p2',
                                'gp_p1', 'gp_p2', 'gp_diff', 'gp_diff_pct',
                                'margin_p1', 'margin_p2', 'margin_diff']].copy()
        l1_show.columns = ['L1 Category', 'BL', '# SKU', 'GV P1', 'GV P2',
                            'GP P1', 'GP P2', 'GP Δ Rp', 'GP Δ %',
                            'Margin P1', 'Margin P2', 'Margin Δ']

        # Style: highlight top/bottom rows
        def highlight_row(row):
            if row['GP Δ Rp'] > 25e6:
                return ['background-color: #ECFDF5'] * len(row)
            elif row['GP Δ Rp'] < -25e6:
                return ['background-color: #FEF2F2'] * len(row)
            return [''] * len(row)

        st.dataframe(
            l1_show.style.format({
                '# SKU': '{:,.0f}',
                'GV P1': '{:,.0f}', 'GV P2': '{:,.0f}',
                'GP P1': '{:,.0f}', 'GP P2': '{:,.0f}', 'GP Δ Rp': '{:,.0f}',
                'GP Δ %': '{:+.2%}',
                'Margin P1': '{:.2%}', 'Margin P2': '{:.2%}', 'Margin Δ': '{:+.4f}',
            }).apply(highlight_row, axis=1),
            use_container_width=True, hide_index=True, height=420
        )

        # ── TABEL L1 BARU: PVM Decomposition per L1 (filter Unit + Scope) ─
        st.markdown("##### 📊 Tabel L1 PVM Decomposition")
        st.caption("PVM effect breakdown per L1 category. Filter unit dan scope di bawah.")

        l1c1, l1c2 = st.columns([1, 1])
        with l1c1:
            l1_unit = st.radio(
                "Unit:",
                ['Rupiah (Rp)', 'Growth %', 'Margin pp', 'Margin pp terhadap Scope'],
                horizontal=True,
                key='l1_unit',
            )
            l1_mode_map = {
                'Rupiah (Rp)': 'rp',
                'Growth %': 'pct',
                'Margin pp': 'pp',
                'Margin pp terhadap Scope': 'pp_contrib',
            }
            l1_mode = l1_mode_map[l1_unit]
        with l1c2:
            l1_scope = st.radio(
                "Scope:",
                ['TOTAL', 'Dry', 'Fresh', 'Frozen', 'PL'],
                horizontal=True,
                key='l1_scope',
            )

        l1_decomp = build_l1_decomp_df(df, scope=l1_scope, mode=l1_mode)
        if l1_decomp.empty:
            st.info("Tidak ada data L1 untuk scope ini.")
        else:
            # Effect columns vary by mode
            base_effect_cols = ['1. Churned', '2. Existing', '  2.1 COGS', '  2.2 Price',
                                '  2.3 Vol/Mix', '3. New']
            if l1_mode == 'pp_contrib':
                effect_cols = base_effect_cols + ['Margin Change Effect', 'GV Weight Effect', 'Total Δ']
            else:
                effect_cols = base_effect_cols + ['Total Δ']

            # Context columns (left side baseline + GV weight, right side end-state + GV weight)
            if l1_mode in ('rp', 'pct'):
                left_context_cols = ['GP P1', 'GV Weight P1']
                right_context_cols = ['GP P2', 'GV Weight P2']
            else:  # pp, pp_contrib
                left_context_cols = ['Margin P1', 'GV Weight P1']
                right_context_cols = ['Margin P2', 'GV Weight P2']

            # Compute Overall row
            overall_row = build_l1_overall_row(df, l1_scope, l1_mode, pvm)
            if overall_row:
                # Convert overall row to DataFrame and append
                overall_df = pd.DataFrame([overall_row])
                l1_full = pd.concat([l1_decomp, overall_df], ignore_index=True)
            else:
                l1_full = l1_decomp.copy()

            # Format cells
            def fmt_effect(v, mode_):
                if pd.isna(v): return '—'
                if mode_ == 'rp':
                    return fmt_rp(v)
                elif mode_ == 'pct':
                    return f"{v:+.2f}%"
                else:  # pp or pp_contrib
                    return f"{v:+.3f}pp"

            def fmt_context_left_right(v, col_name, mode_):
                if pd.isna(v): return '—'
                if col_name in ('GV Weight P1', 'GV Weight P2'):
                    return f"{v*100:.2f}%"
                elif col_name in ('GP P1', 'GP P2'):
                    return fmt_rp(v)
                else:  # Margin P1, Margin P2
                    return f"{v:.2f}%"

            display = l1_full.copy()
            for col in effect_cols:
                if col in display.columns:
                    display[col] = display[col].apply(lambda v: fmt_effect(v, l1_mode))
            for col in left_context_cols + right_context_cols:
                if col in display.columns:
                    display[col] = display.apply(lambda r: fmt_context_left_right(r[col], col, l1_mode), axis=1)

            # Reorder columns: L1 | BL | left_context | effects | right_context
            ordered_cols = ['L1 Category', 'BL'] + left_context_cols + effect_cols + right_context_cols
            display = display[[c for c in ordered_cols if c in display.columns]]

            # Gradient coloring on numeric values (effects only)
            def style_l1_gradient(df_orig, df_disp):
                num_cols = [c for c in effect_cols if c in df_orig.columns]
                # Exclude Overall row from vmax calc to avoid scale issue
                non_overall_mask = ~df_orig['L1 Category'].astype(str).str.startswith('OVERALL')
                vals = df_orig.loc[non_overall_mask, num_cols].values.flatten()
                vals = [v for v in vals if pd.notna(v)]
                vmax = max(abs(v) for v in vals) if vals else 1
                if vmax == 0: vmax = 1

                def color_cell(val_numeric):
                    if pd.isna(val_numeric): return ''
                    norm = max(-1, min(1, val_numeric / vmax))
                    if norm > 0:
                        alpha = norm
                        r = int(255 - (255-22) * alpha)
                        g = int(255 - (255-163) * alpha)
                        b = int(255 - (255-74) * alpha)
                        return f'background-color: rgb({r},{g},{b}); color: #111827;'
                    elif norm < 0:
                        alpha = -norm
                        r = int(255 - (255-220) * alpha)
                        g = int(255 - (255-38) * alpha)
                        b = int(255 - (255-38) * alpha)
                        text_color = '#FFFFFF' if alpha > 0.6 else '#111827'
                        return f'background-color: rgb({r},{g},{b}); color: {text_color};'
                    return ''

                def apply_style(row):
                    is_overall = str(df_orig.loc[row.name, 'L1 Category']).startswith('OVERALL')
                    styles = []
                    for col in df_disp.columns:
                        if is_overall:
                            styles.append('background-color: #DBEAFE; font-weight: 700;')
                        elif col in num_cols:
                            val_num = df_orig.loc[row.name, col]
                            styles.append(color_cell(val_num))
                        else:
                            styles.append('')
                    return styles

                return df_disp.style.apply(apply_style, axis=1)

            unit_label_l1 = {
                'rp': 'Rupiah',
                'pct': 'GP Growth %',
                'pp': 'Margin pp (within L1)',
                'pp_contrib': f'Margin pp Contribution to {l1_scope}'
            }[l1_mode]
            n_l1 = len(l1_decomp)
            st.markdown(f"**Unit: {unit_label_l1} · Scope: {l1_scope}** · {n_l1} L1 categories + Overall row")

            st.dataframe(
                style_l1_gradient(l1_full, display),
                use_container_width=True, hide_index=True, height=650
            )

            # Footer caption with methodology note
            if l1_mode == 'pp_contrib':
                total_mc = l1_decomp['Margin Change Effect'].sum()
                total_gv_wt = l1_decomp['GV Weight Effect'].sum()
                total_combined = l1_decomp['Total Δ'].sum()
                actual_scope_pp = pvm[l1_scope]['pp_total'] * 100
                st.caption(
                    f"💡 **Math identity (sum-able):** Σ Margin Change Effect ({total_mc:+.3f}pp) + "
                    f"Σ GV Weight Effect ({total_gv_wt:+.3f}pp) = "
                    f"**{total_combined:+.3f}pp** = scope {l1_scope} actual ΔMargin "
                    f"(**{actual_scope_pp:+.3f}pp**) ✓ exact match."
                )
            elif l1_mode == 'rp':
                total_rp = l1_decomp['Total Δ'].sum()
                actual_rp = pvm[l1_scope]['gp_end'] - pvm[l1_scope]['gp_start']
                st.caption(
                    f"💡 **Sum-able:** Σ L1 Rp ({fmt_rp(total_rp)}) = "
                    f"scope {l1_scope} actual GP Δ ({fmt_rp(actual_rp)}) ✓ exact match. "
                    f"Row Overall = Sum of all L1."
                )
            elif l1_mode == 'pct':
                st.caption(
                    f"⚠️ **Non-sum-able:** Growth % per L1 = Rp_diff / L1_GP_p1. "
                    f"Sum of L1 growth ≠ Scope growth (denominator berbeda). "
                    f"Row Overall = scope-level aggregate ({(pvm[l1_scope]['gp_end']-pvm[l1_scope]['gp_start'])/pvm[l1_scope]['gp_start']*100:+.2f}%), "
                    f"dihitung fresh dari scope totals."
                )
            else:  # pp
                st.caption(
                    f"⚠️ **Non-sum-able:** Margin pp per L1 = m_end_L1 - m_base_L1. "
                    f"Setiap L1 punya base margin berbeda, sum of pp tanpa weighting = meaningless. "
                    f"Row Overall = scope-level aggregate margin change ({pvm[l1_scope]['pp_total']*100:+.3f}pp), "
                    f"dihitung dari scope's aggregate margin (bukan sum of L1)."
                )

    # ─────────────────────────────────────────────────────────────────────
    # ZONE 4.5 — TOP MOVERS (3 SECTIONS: GP / PRICE / COGS)
    # ─────────────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">🔝 Top Movers (Existing SKU only)</div>', unsafe_allow_html=True)
    st.caption("Per-SKU decomposition: COGS + Price + Vol/Mix Effect sum to GP Δ. "
               "Note: di per-SKU level, Vol/Mix Effect = qty change × unit margin P2 (pure volume; "
               "mix shift hanya bermakna di aggregate level).")

    name_col = 'product_name' if 'product_name' in df.columns else ('sku_name' if 'sku_name' in df.columns else None)
    id_col = 'product_id' if 'product_id' in df.columns else ('sku_id' if 'sku_id' in df.columns else None)

    def mover_table_full(d):
        """Build full table with decomposition + Δ Rp + Growth % + Margin P1→P2."""
        rows = []
        for i, (_, r) in enumerate(d.iterrows(), 1):
            name = r.get(name_col, '—') if name_col else '—'
            bl = r.get('pricing_bl', '—')
            l1 = r.get('l1_category', '—')

            gp_d = r.get('gp_diff', 0)
            cogs_eff = r.get('cogs_effect', 0)
            price_eff = r.get('price_effect', 0)
            volmix_eff = r.get('volmix_effect', 0)
            gp_growth = r.get('gp_growth_pct', np.nan)

            price_diff_rp = r.get('price_diff_rp', 0)
            price_diff_pct = r.get('price_diff_pct', np.nan)
            cogs_diff_rp = r.get('cogs_diff_rp', 0)
            cogs_diff_pct = r.get('cogs_diff_pct', np.nan)

            # Margin P1 → P2
            mgn_p1 = r.get('margin_p1_pct', np.nan)
            mgn_p2 = r.get('margin_p2_pct', np.nan)
            if pd.notna(mgn_p1) and pd.notna(mgn_p2):
                mgn_txt = f"{mgn_p1:.1f}% → {mgn_p2:.1f}%"
            else:
                mgn_txt = "—"

            qty_pct = r.get('qty_diff_pct', np.nan)
            comp_s = r.get('comp_status', '—') or '—'

            # Avg Stock + OOS detection
            stock_p1 = r.get('avg_stock_p1', np.nan)
            stock_p2 = r.get('avg_stock_p2', np.nan)
            stock_growth = r.get('avg_stock_growth_pct', np.nan)
            # OOS flag: stock_growth <= -10% → driver auto-fill
            if pd.notna(stock_growth) and stock_growth <= -10:
                driver_txt = "⚠️ OOS risk"
            else:
                driver_txt = ''

            pi_p1 = r.get('pi_p1', np.nan)
            pi_p2 = r.get('pi_p2', np.nan)
            pi_txt = f"{pi_p1:.0f}→{pi_p2:.0f}" if pd.notna(pi_p1) and pd.notna(pi_p2) else "—"

            rows.append({
                '#': i,
                'Product': str(name)[:35],
                'BL': bl,
                'L1': l1,
                'GP Δ Rp': gp_d,
                'COGS Effect': cogs_eff,
                'Price Effect': price_eff,
                'Vol/Mix Effect': volmix_eff,
                'GP Growth %': gp_growth,
                'Mgn P1 → P2': mgn_txt,
                'Price Δ Rp': price_diff_rp,
                'Price Δ%': price_diff_pct,
                'COGS Δ Rp': cogs_diff_rp,
                'COGS Δ%': cogs_diff_pct,
                'Qty Δ%': qty_pct,
                'Stock P1': stock_p1,
                'Stock P2': stock_p2,
                'Stock Growth %': stock_growth,
                'Comp': comp_s,
                'PI': pi_txt,
                'Driver': driver_txt,
            })
        return pd.DataFrame(rows)

    fmt_movers = {
        'GP Δ Rp': '{:+,.0f}',
        'COGS Effect': '{:+,.0f}',
        'Price Effect': '{:+,.0f}',
        'Vol/Mix Effect': '{:+,.0f}',
        'GP Growth %': '{:+.1f}%',
        'Price Δ Rp': '{:+,.0f}',
        'Price Δ%': '{:+.2%}',
        'COGS Δ Rp': '{:+,.0f}',
        'COGS Δ%': '{:+.2%}',
        'Qty Δ%': '{:+.1%}',
        'Stock P1': '{:,.0f}',
        'Stock P2': '{:,.0f}',
        'Stock Growth %': '{:+.1f}%',
    }

    # ── SECTION A: TOP GP MOVERS ────────────────────────────────────────
    st.markdown("### A. Top 30 GP Movers")
    gp_gainers, gp_losers = compute_top_movers_gp(df, n=30)
    mv_a1, mv_a2 = st.columns(2)
    with mv_a1:
        st.markdown("**🟢 Top 30 GP Gainers**")
        df_a1 = mover_table_full(gp_gainers)
        st.dataframe(df_a1.style.format(fmt_movers), use_container_width=True, hide_index=True, height=600)
    with mv_a2:
        st.markdown("**🔴 Top 30 GP Losers**")
        df_a2 = mover_table_full(gp_losers)
        st.dataframe(df_a2.style.format(fmt_movers), use_container_width=True, hide_index=True, height=600)

    # ── SECTION B: TOP PRICE MOVERS ─────────────────────────────────────
    st.markdown("### B. Top 30 Price Movers")
    price_ups, price_downs = compute_top_movers_price(df, n=30)
    mv_b1, mv_b2 = st.columns(2)
    with mv_b1:
        st.markdown("**🔼 Top 30 Price Up**")
        df_b1 = mover_table_full(price_ups)
        st.dataframe(df_b1.style.format(fmt_movers), use_container_width=True, hide_index=True, height=600)
    with mv_b2:
        st.markdown("**🔽 Top 30 Price Down**")
        df_b2 = mover_table_full(price_downs)
        st.dataframe(df_b2.style.format(fmt_movers), use_container_width=True, hide_index=True, height=600)

    # ── SECTION C: TOP COGS MOVERS ──────────────────────────────────────
    st.markdown("### C. Top 30 COGS Movers")
    cogs_ups, cogs_downs = compute_top_movers_cogs(df, n=30)
    mv_c1, mv_c2 = st.columns(2)
    with mv_c1:
        st.markdown("**🔼 Top 30 COGS Up**")
        df_c1 = mover_table_full(cogs_ups)
        st.dataframe(df_c1.style.format(fmt_movers), use_container_width=True, hide_index=True, height=600)
    with mv_c2:
        st.markdown("**🔽 Top 30 COGS Down**")
        df_c2 = mover_table_full(cogs_downs)
        st.dataframe(df_c2.style.format(fmt_movers), use_container_width=True, hide_index=True, height=600)

    # ─────────────────────────────────────────────────────────────────────
    # ZONE 5 — SKU WATCH LIST (PRIORITY)
    # ─────────────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">5️⃣ SKU Watch List — Priority</div>', unsafe_allow_html=True)

    priority = compute_watch_priority(df)
    n_priority = len(priority)

    # Also get Review/Adjust/Framework counts for context
    n_review = (df['flag_price'].isin(['Review', 'Adjust'])).sum() if 'flag_price' in df.columns else 0
    n_framework_check = (df['framework_check'] == True).sum() if 'framework_check' in df.columns else 0

    st.markdown(f"""
        Hari ini ada **{n_priority} SKU Priority** yang butuh attention urgent.
        Definisi Priority: (COGS↑ + Comp↑ + Price flat = room to raise) ATAU (COGS↓ + Comp↓ + Price flat = room to drop).
    """)

    if n_priority == 0:
        st.info("Tidak ada SKU Priority. ✅")
    else:
        # Display priority SKUs
        wl_cols = ['product_id', 'product_name', 'pricing_bl', 'l1_category',
                   'price_status', 'cogs_status', 'comp_status',
                   'price_p1', 'price_p2', 'cogs_p1', 'cogs_p2',
                   'comp_price_p1', 'comp_price_p2', 'pi_p1', 'pi_p2',
                   'gp_p1', 'gp_p2', 'gp_diff']
        wl_cols = [c for c in wl_cols if c in priority.columns]
        wl = priority[wl_cols].copy()

        # Add suggested action
        def suggest_action(r):
            if r.get('cogs_status') == 'Up' and r.get('comp_status') == 'Up':
                return '🔼 Raise price'
            if r.get('cogs_status') == 'Drop' and r.get('comp_status') == 'Drop':
                return '🔽 Drop price'
            return '—'
        wl['Suggested Action'] = wl.apply(suggest_action, axis=1)

        rename_map = {
            'product_id': 'SKU ID', 'product_name': 'Product', 'pricing_bl': 'BL', 'l1_category': 'L1',
            'price_status': 'Price', 'cogs_status': 'COGS', 'comp_status': 'Comp',
            'price_p1': 'Price P1', 'price_p2': 'Price P2',
            'cogs_p1': 'COGS P1', 'cogs_p2': 'COGS P2',
            'comp_price_p1': 'Comp P1', 'comp_price_p2': 'Comp P2',
            'pi_p1': 'PI P1', 'pi_p2': 'PI P2',
            'gp_p1': 'GP P1', 'gp_p2': 'GP P2', 'gp_diff': 'GP Δ',
        }
        wl = wl.rename(columns=rename_map)

        st.dataframe(
            wl.style.format({
                'Price P1': '{:,.0f}', 'Price P2': '{:,.0f}',
                'COGS P1': '{:,.0f}', 'COGS P2': '{:,.0f}',
                'Comp P1': '{:,.0f}', 'Comp P2': '{:,.0f}',
                'PI P1': '{:.1f}', 'PI P2': '{:.1f}',
                'GP P1': '{:,.0f}', 'GP P2': '{:,.0f}', 'GP Δ': '{:+,.0f}',
            }),
            use_container_width=True, hide_index=True, height=400
        )

    st.caption(f"📌 Total dari sheet 7 SKU Watch List: **{n_priority} Priority** · "
               f"{n_review} Review/Adjust · {n_framework_check} Framework Check. "
               f"Download Full Excel di bawah untuk akses lengkap.")

    # ─────────────────────────────────────────────────────────────────────
    # DOWNLOAD FULL EXCEL
    # ─────────────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">💾 Download Output</div>', unsafe_allow_html=True)
    st.caption(f"File output: 12 sheet identical dengan `pvm_analyzer_v3.py`. Size: {len(A['excel_bytes'])/1024/1024:.1f} MB.")
    st.download_button(
        f"📥 Download Full Excel ({p1}_vs_{p2}_enriched.xlsx)",
        data=A['excel_bytes'],
        file_name=f"{p1}_vs_{p2}_enriched.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
        use_container_width=False,
    )

else:
    # No data state
    st.info("👆 Upload file Excel atau CSV untuk mulai analisis. Klik **Download Template** kalau butuh contoh format.")
