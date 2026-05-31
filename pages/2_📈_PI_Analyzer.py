"""
PI Analyzer — Streamlit Web App (Page 2)
Pricing Index movement decomposition vs competitor.

Author: Shadqi (Pricing Strategy Analyst, Astro)
"""
import io
import sys
import os
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Add parent dir to path so we can import pi_analyzer_v1
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pi_analyzer_v1 import compute as pi_compute, generate_excel as pi_generate_excel

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PI Analyzer — Astro Pricing",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="auto",
)


# ─────────────────────────────────────────────────────────────────────────────
# CACHED HELPERS (analytical computation cached by file hash)
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False, max_entries=3)
def cached_pi_compute(file_bytes, file_name):
    """Cache PI compute result by file content hash. Excel NOT included."""
    import io
    if file_name.lower().endswith('.csv'):
        df = pd.read_csv(io.BytesIO(file_bytes))
    else:
        df = pd.read_excel(io.BytesIO(file_bytes))
    return pi_compute(df)


@st.cache_data(show_spinner=False, max_entries=2)
def cached_pi_excel_bytes(file_bytes, file_name):
    """Cache Excel workbook bytes (separate cache from compute)."""
    import io
    result = cached_pi_compute(file_bytes, file_name)
    wb = pi_generate_excel(result)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()

# Custom CSS — mirror Page 1
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
    .banner-info {
        background: #DBEAFE;
        border-left: 4px solid #2563EB;
        padding: 12px 16px;
        border-radius: 6px;
        margin-bottom: 16px;
    }
    .section-header {
        font-size: 22px;
        font-weight: 700;
        color: #111827;
        margin-top: 32px;
        margin-bottom: 12px;
        padding-bottom: 8px;
        border-bottom: 2px solid #E5E7EB;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
REQUIRED_COLS = [
    'product_id', 'product_name', 'l1_category_name', 'pricing_bl_25',
    'pareto_classification', 'source_status',
    'price', 'next_price', 'cogs', 'next_cogs',
    'comp_price', 'next_comp_price',
    'normal_comp_price', 'next_normal_comp_price',
    'pi', 'next_pi',
]
PERIOD_PAIRS = [('week_key', 'next_week'), ('month_key', 'next_month')]

SEGMENTS = ['Dry', 'Fresh', 'Frozen']

PI_BINS_LBL  = ["A.<95", "B.95-<100", "C.100-105", "D.105-110", "E.110-120", "F.>120"]
CI_BINS_LBL  = ["A.<70", "B.70-85", "C.85-95", "D.95-105", "E.>105"]
MG_BINS_LBL  = ["A.<-20%", "B.-20to-10%", "C.-10to0%", "D.0to10%",
                "E.10to20%", "F.20to30%", "G.30to50%", "H.>50%"]

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def fmt_pi(v, decimals=2):
    """Format PI value (just a number, no unit since PI is unitless ratio)."""
    if pd.isna(v): return "—"
    return f"{v:,.{decimals}f}"

def fmt_pi_delta(v, decimals=3):
    """Format PI delta with sign."""
    if pd.isna(v): return "—"
    return f"{v:+.{decimals}f}"

def fmt_pct(v, decimals=2):
    if pd.isna(v): return "—"
    return f"{v*100:.{decimals}f}%"

def fmt_count(v):
    if pd.isna(v): return "—"
    return f"{int(v):,}"

def kpi_card(label, value, delta=None, delta_label=None, sub=None, delta_inverse=False):
    """Build HTML for KPI card."""
    delta_html = ""
    if delta is not None and delta_label is not None:
        if delta == 0:
            cls = "kpi-delta-neu"
            arrow = "—"
        else:
            # delta_inverse=True means lower=better (e.g. PI lower vs competitor)
            is_positive = delta > 0
            if delta_inverse:
                cls = "kpi-delta-neg" if is_positive else "kpi-delta-pos"
            else:
                cls = "kpi-delta-pos" if is_positive else "kpi-delta-neg"
            arrow = "▲" if is_positive else "▼"
        delta_html = f'<div class="{cls}">{arrow} {delta_label}</div>'

    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""

    return f'''<div class="kpi-card">
<div class="kpi-label">{label}</div>
<div class="kpi-value">{value}</div>
{delta_html}
{sub_html}
</div>'''


def gradient_color(val, vmax):
    """Return CSS background+text color for gradient red-white-green."""
    if pd.isna(val): return ''
    if vmax == 0: return ''
    norm = max(-1, min(1, val / vmax))
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


def make_template_pi_excel():
    """Generate a template Excel with required columns."""
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Raw Input Template"

    headers = ['week_key', 'next_week'] + REQUIRED_COLS
    for c, h in enumerate(headers, 1):
        ws.cell(1, c, h)

    # Add note
    ws.cell(3, 1, "Note: Required period cols: 'week_key' + 'next_week' OR 'month_key' + 'next_month'")
    ws.cell(4, 1, "All numeric cols (price, cogs, comp_price, normal_comp_price, pi) bisa NaN untuk New/Departing SKU.")

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# TORNADO CHART (Zone 3)
# ─────────────────────────────────────────────────────────────────────────────
def make_pi_tornado(decomp_dict, scope_label='Overall'):
    """
    Tornado horizontal bar chart of 5 PI effect components.
    Components: eff_dep (Churned), eff_price, eff_normal_comp, eff_discount_comp, eff_new.
    """
    components = [
        ('1. Churned SKU Effect', decomp_dict['eff_dep']),
        ('2. Price Change Effect',       decomp_dict['eff_price']),
        ('3.1 Normal Comp Price Effect', decomp_dict['eff_normal_comp']),
        ('3.2 Discount (Blended) Comp Price Effect', decomp_dict['eff_discount_comp']),
        ('4. New SKU Effect',     decomp_dict['eff_new']),
    ]
    # Sort by magnitude desc
    sorted_comp = sorted(components, key=lambda x: abs(x[1]), reverse=True)
    labels = [c[0] for c in sorted_comp][::-1]
    values = [c[1] for c in sorted_comp][::-1]
    colors = ['#059669' if v >= 0 else '#DC2626' for v in values]
    text_vals = [f"{v:+.3f}" for v in values]

    total = decomp_dict.get('total', sum(c[1] for c in components))

    fig = go.Figure(go.Bar(
        x=values,
        y=labels,
        orientation='h',
        marker_color=colors,
        text=text_vals,
        textposition='outside',
        cliponaxis=False,
    ))
    fig.update_layout(
        title=f"PI Movement Decomposition — {scope_label}  |  Total Δ: {total:+.3f} (A={decomp_dict['A']:.2f} → E={decomp_dict['E']:.2f})",
        showlegend=False,
        height=420,
        margin=dict(l=20, r=80, t=60, b=40),
        xaxis_title='PI points',
        plot_bgcolor='white',
        bargap=0.35,
    )
    fig.update_xaxes(showgrid=True, gridcolor='#F3F4F6', zeroline=True,
                     zerolinecolor='#9CA3AF', zerolinewidth=2)
    fig.update_yaxes(showgrid=False)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# BUILDER: Tabel PI Decomposition per Scope (Zone 3 Tabel)
# ─────────────────────────────────────────────────────────────────────────────
def build_pi_decomp_table(overall, segments, contribs):
    """
    Tabel 1: Per-segment PI decomposition with overall column.
    Methodology mirrors Sheet 2 in Excel output.
    Rows: A baseline, 5 effect components, E result, Total Δ.
    Cols: Overall, Dry, Fresh, Frozen.
    """
    rows = []
    rows.append({
        'Step': 'Baseline — Avg PI Prev (A)',
        'Overall': overall['A'],
        'Dry':     segments['Dry']['A'],
        'Fresh':   segments['Fresh']['A'],
        'Frozen':  segments['Frozen']['A'],
    })
    for label, key in [
        ('+ 1. Churned SKU Effect',          'eff_dep'),
        ('+ 2. Price Change Effect',         'eff_price'),
        ('+ 3. Comp Price Effect',  'eff_comp'),
        ('    3.1 Normal Comp Price Effect',       'eff_normal_comp'),
        ('    3.2 Discount (Blended) Comp Price Effect', 'eff_discount_comp'),
        ('+ 4. New SKU Effect',              'eff_new'),
    ]:
        rows.append({
            'Step': label,
            'Overall': overall[key],
            'Dry':     segments['Dry'][key],
            'Fresh':   segments['Fresh'][key],
            'Frozen':  segments['Frozen'][key],
        })
    rows.append({
        'Step': 'Result — Avg PI Cur (E)',
        'Overall': overall['E'],
        'Dry':     segments['Dry']['E'],
        'Fresh':   segments['Fresh']['E'],
        'Frozen':  segments['Frozen']['E'],
    })
    rows.append({
        'Step': 'Total Δ',
        'Overall': overall['total'],
        'Dry':     segments['Dry']['total'],
        'Fresh':   segments['Fresh']['total'],
        'Frozen':  segments['Frozen']['total'],
    })
    return pd.DataFrame(rows)


def build_pi_contrib_table(overall, contribs):
    """
    Tabel 2: Per-segment contribution to OVERALL effect (exact math identity).
    Each cell = exact_contributions formula. Sum across segments = overall (exact).
    """
    rows = []
    for label, key in [
        ('1. Churned SKU Effect',                  'eff_dep'),
        ('2. Price Change Effect',                 'eff_price'),
        ('3. Comp Price Effect',          'eff_comp'),
        ('  3.1 Normal Comp Price Effect',               'eff_normal_comp'),
        ('  3.2 Discount (Blended) Comp Price Effect',   'eff_discount_comp'),
        ('4. New SKU Effect',                      'eff_new'),
    ]:
        rows.append({
            'Effect': label,
            'Dry contrib':    contribs['Dry'][key],
            'Fresh contrib':  contribs['Fresh'][key],
            'Frozen contrib': contribs['Frozen'][key],
            'Overall (sum)':  contribs['Dry'][key] + contribs['Fresh'][key] + contribs['Frozen'][key],
            'Overall actual': overall[key],
        })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# BUILDER: L1 Decomposition (Zone 4)
# ─────────────────────────────────────────────────────────────────────────────
def build_l1_pi_table(df, scope='Overall'):
    """
    For each L1 category, run decompose() and return table.
    scope: 'Overall' = all SKU, else filter by BL (Dry/Fresh/Frozen).
    """
    from pi_analyzer_v1 import decompose

    if scope != 'Overall':
        df_scope = df[df['pricing_bl_25'] == scope].copy()
    else:
        df_scope = df.copy()

    if 'l1_category_name' not in df_scope.columns or len(df_scope) == 0:
        return pd.DataFrame()

    rows = []
    for l1, g in df_scope.groupby('l1_category_name', dropna=False):
        if pd.isna(l1):
            continue
        r = decompose(g)
        ex_sub = g[g['sku_type'] == 'Existing']
        rows.append({
            'L1 Category': l1,
            'BL (sample)': g['pricing_bl_25'].iloc[0] if 'pricing_bl_25' in g.columns else '—',
            'n Existing':  r['n_ex'],
            'n Departing': r['n_dep'],
            'n New':       r['n_new'],
            'Avg PI Prev (A)': r['A'],
            'Avg PI Cur (E)':  r['E'],
            'Total Δ':         r['total'],
            '1. Churned Eff':  r['eff_dep'],
            '2. Price Eff':    r['eff_price'],
            '3. Comp Price Eff':     r['eff_comp'],
            '3.1 Normal Comp Eff': r['eff_normal_comp'],
            '3.2 Discount Comp Eff': r['eff_discount_comp'],
            '4. New SKU Eff':      r['eff_new'],
        })

    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values('Total Δ', ascending=False).reset_index(drop=True)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# BUILDER: Pareto Decomposition (Zone 11)
# ─────────────────────────────────────────────────────────────────────────────
def build_pareto_pi_table(df, scope='Overall'):
    """Same structure as L1 but dimension = pareto_classification."""
    from pi_analyzer_v1 import decompose

    if scope != 'Overall':
        df_scope = df[df['pricing_bl_25'] == scope].copy()
    else:
        df_scope = df.copy()

    if 'pareto_classification' not in df_scope.columns or len(df_scope) == 0:
        return pd.DataFrame()

    rows = []
    for pareto, g in df_scope.groupby('pareto_classification', dropna=False):
        if pd.isna(pareto):
            continue
        r = decompose(g)
        rows.append({
            'Pareto Class':    pareto,
            'n Existing':      r['n_ex'],
            'n Departing':     r['n_dep'],
            'n New':           r['n_new'],
            'Avg PI Prev (A)': r['A'],
            'Avg PI Cur (E)':  r['E'],
            'Total Δ':         r['total'],
            '1. Churned Eff':  r['eff_dep'],
            '2. Price Eff':    r['eff_price'],
            '3. Comp Price Eff':     r['eff_comp'],
            '3.1 Normal Comp Eff': r['eff_normal_comp'],
            '3.2 Discount Comp Eff': r['eff_discount_comp'],
            '4. New SKU Eff':      r['eff_new'],
        })

    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values('Pareto Class').reset_index(drop=True)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# BUILDER: Price × Comp Matrix (Zone 5)
# ─────────────────────────────────────────────────────────────────────────────
def build_price_comp_matrix(df, scope='Overall'):
    """
    3×3 matrix: rows = price_tag (Down/Stay/Up), cols = comp_tag (Down/Stay/Up).
    Cells = count of Existing SKU.
    """
    if scope != 'Overall':
        df_scope = df[df['pricing_bl_25'] == scope].copy()
    else:
        df_scope = df.copy()

    ex = df_scope[df_scope['sku_type'] == 'Existing']
    if len(ex) == 0:
        return None, None

    DIRS = ['Down', 'Stay', 'Up']
    matrix = np.zeros((3, 3), dtype=int)
    for ri, pr in enumerate(DIRS):
        for ci, cr in enumerate(DIRS):
            matrix[ri, ci] = int(((ex['price_tag'] == pr) & (ex['comp_tag'] == cr)).sum())

    df_matrix = pd.DataFrame(
        matrix,
        index=[f'PRICE {d}' for d in DIRS],
        columns=[f'COMP {d}' for d in DIRS],
    )
    return df_matrix, len(ex)


# ─────────────────────────────────────────────────────────────────────────────
# BUILDER: PI Distribution (Zone 6)
# ─────────────────────────────────────────────────────────────────────────────
def build_pi_distribution(df, scope='Overall'):
    """PI bucket distribution Prev vs Cur. Existing SKU only."""
    if scope != 'Overall':
        df_scope = df[df['pricing_bl_25'] == scope].copy()
    else:
        df_scope = df.copy()

    ex = df_scope[df_scope['sku_type'] == 'Existing']
    n = len(ex)
    if n == 0:
        return pd.DataFrame()

    rows = []
    for lbl in PI_BINS_LBL:
        nc = int((ex['pi_group_prev'].astype(str) == lbl).sum())
        nn = int((ex['pi_group_cur'].astype(str) == lbl).sum())
        rows.append({
            'PI Bucket': lbl,
            'n Prev':    nc,
            'n Cur':     nn,
            'Δ Count':   nn - nc,
            '% Prev':    nc/n if n > 0 else 0,
            '% Cur':     nn/n if n > 0 else 0,
            'Δ %':       (nn - nc)/n if n > 0 else 0,
        })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# BUILDER: Top Movers SKU (Zone 7)
# ─────────────────────────────────────────────────────────────────────────────
def build_top_movers_pi(df, n=30):
    """Top N gainers + losers by absolute |diff_pi|."""
    ex = df[df['sku_type'] == 'Existing'].dropna(subset=['diff_pi']).copy()
    if len(ex) == 0:
        return pd.DataFrame(), pd.DataFrame()

    gainers = ex.nlargest(n, 'diff_pi')
    losers = ex.nsmallest(n, 'diff_pi')
    return gainers, losers


def fmt_mover_row(r, idx):
    """Format single row for mover table display."""
    pi_p1 = r.get('pi', np.nan)
    pi_p2 = r.get('next_pi', np.nan)
    mgn_p1 = r.get('margin_pct_prev', np.nan)
    mgn_p2 = r.get('margin_pct_cur', np.nan)
    return {
        '#': idx,
        'Product': str(r.get('product_name', '—'))[:35],
        'BL': r.get('pricing_bl_25', '—'),
        'L1': r.get('l1_category_name', '—'),
        'PI P1 → P2': f"{pi_p1:.1f} → {pi_p2:.1f}" if pd.notna(pi_p1) and pd.notna(pi_p2) else "—",
        'Δ PI': r.get('diff_pi', 0),
        'Price Eff': r.get('eff_price', 0),
        'Comp Price Eff': r.get('eff_comp', 0),
        'Normal Comp Eff': r.get('eff_normal_comp', 0),
        'Discount Comp Eff': r.get('eff_discount_comp', 0),
        'Mgn P1 → P2': f"{mgn_p1*100:.1f}% → {mgn_p2*100:.1f}%" if pd.notna(mgn_p1) and pd.notna(mgn_p2) else "—",
        'Price Δ%': r.get('diff_price_pct', np.nan),
        'COGS Δ%': r.get('diff_cogs_pct', np.nan),
        'Framework': r.get('framework_check', '') or '',
    }


# ─────────────────────────────────────────────────────────────────────────────
# BUILDER: Framework Check (Zone 9)
# ─────────────────────────────────────────────────────────────────────────────
def build_framework_check_table(df):
    """Filter SKU where framework_check == 'TRUE' and classify by rule."""
    fc = df[df['framework_check'] == 'TRUE'].copy()
    if len(fc) == 0:
        return pd.DataFrame()

    # Classify rule based on conditions
    def classify_rule(row):
        bl = row.get('pricing_bl_25', '')
        pi = row.get('next_pi', np.nan)
        mg = row.get('margin_pct_cur', np.nan)
        if pd.isna(pi) or pd.isna(mg):
            return 'Unknown'
        if bl == 'Fresh':
            if pi > 110 and mg <= 0.15: return 'Rule 1: Fresh PI>110 + Margin≤15% (room to drop price)'
            if pi > 120 and mg >= 0.70: return 'Rule 3: Fresh PI>120 + Margin≥70% (over-priced premium)'
        elif bl == 'Frozen':
            if pi > 100 and mg <= 0.15: return 'Rule 2: Frozen PI>100 + Margin≤15% (room to drop)'
        elif bl == 'Dry':
            if pi < 105 and mg <= 0.00: return 'Rule 4: Dry PI<105 + Margin≤0% (loss leader, raise)'
            if pi > 120 and mg > 0.40: return 'Rule 5: Dry PI>120 + Margin>40% (over-priced, drop)'
        return 'Other'

    fc['Rule'] = fc.apply(classify_rule, axis=1)

    cols = ['Rule', 'product_id', 'product_name', 'pricing_bl_25', 'l1_category_name',
            'pi', 'next_pi', 'diff_pi', 'margin_pct_prev', 'margin_pct_cur',
            'price', 'next_price', 'cogs', 'next_cogs', 'comp_price', 'next_comp_price']
    cols = [c for c in cols if c in fc.columns]
    out = fc[cols].sort_values(['Rule', 'next_pi'], ascending=[True, False]).reset_index(drop=True)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# BUILDER: Structural Loss (Zone 8a) + COGS Need Improve (Zone 8b)
# ─────────────────────────────────────────────────────────────────────────────
def build_structural_loss(df):
    """L1 categories with high CI Group D (95-105) or E (>105)."""
    ex = df[df['ci_cur'].notna() & df['next_pi'].notna() & df['margin_pct_cur'].notna()].copy()
    if len(ex) == 0:
        return pd.DataFrame()

    cat_total = ex.groupby('l1_category_name').size().to_dict()
    rows = []
    for grp_label, grp_filter in [
        ('COGS Index D (95-105)', 'D.95-105'),
        ('COGS Index E (>105)',   'E.>105'),
    ]:
        sub = ex[ex['ci_group_cur'] == grp_filter]
        if len(sub) == 0:
            continue
        by_cat = sub.groupby('l1_category_name').agg(
            n_sku=('product_id', 'count'),
            avg_ci=('ci_cur', 'mean'),
            avg_mg=('margin_pct_cur', 'mean'),
            avg_pi=('next_pi', 'mean')
        ).sort_values('n_sku', ascending=False).reset_index()
        for _, row in by_cat.iterrows():
            pct = row['n_sku'] / cat_total.get(row['l1_category_name'], 1)
            rows.append({
                'CI Group': grp_label,
                'L1 Category': row['l1_category_name'],
                'n SKU': int(row['n_sku']),
                '% of Category': pct,
                'Avg COGS Index': row['avg_ci'],
                'Avg Margin %': row['avg_mg'],
                'Avg PI (Cur)': row['avg_pi'],
            })

    return pd.DataFrame(rows)


def build_cogs_need_improve(df):
    """SKU list with CI Group D or E. Sorted by CI desc."""
    ex = df[df['ci_group_cur'].isin(['D.95-105', 'E.>105'])].copy()
    if len(ex) == 0:
        return pd.DataFrame()
    ex = ex.sort_values('ci_cur', ascending=False)
    cols = ['product_id', 'product_name', 'l1_category_name', 'pricing_bl_25',
            'pareto_classification', 'sku_type',
            'ci_group_cur', 'ci_cur', 'next_pi', 'margin_pct_cur',
            'next_price', 'next_cogs', 'next_comp_price']
    cols = [c for c in cols if c in ex.columns]
    return ex[cols].reset_index(drop=True)


# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
if 'pi_analysis' not in st.session_state:
    st.session_state.pi_analysis = None
if 'pi_file_bytes' not in st.session_state:
    st.session_state.pi_file_bytes = None
if 'pi_uploaded_file_name' not in st.session_state:
    st.session_state.pi_uploaded_file_name = None
if 'pi_uploaded_file_size' not in st.session_state:
    st.session_state.pi_uploaded_file_size = None


# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────
col_title, col_clear = st.columns([5, 1])
with col_title:
    st.title("📈 PI Analyzer")
    st.caption("Pricing Index Movement Decomposition vs Competitor — Astro Pricing Strategy")
with col_clear:
    st.write("")
    if st.session_state.pi_analysis is not None:
        if st.button("🗑️ Clear data", type="secondary", use_container_width=True, key='pi_clear'):
            st.session_state.pi_analysis = None
            st.session_state.pi_file_bytes = None
            st.session_state.pi_uploaded_file_name = None
            st.session_state.pi_uploaded_file_size = None
            st.session_state.pi_excel_ready = False
            if 'pi_excel_bytes' in st.session_state:
                del st.session_state.pi_excel_bytes
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# ZONE 1 — UPLOAD
# ═══════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">📁 Upload Data</div>', unsafe_allow_html=True)

up_col1, up_col2 = st.columns([3, 1])
with up_col1:
    uploaded = st.file_uploader(
        "Upload file Excel atau CSV (raw input per-SKU per-periode)",
        type=['xlsx', 'xls', 'csv'],
        help=f"Format mengikuti pi_analyzer_v1.py. Required columns: {', '.join(REQUIRED_COLS[:8])}...",
        key='pi_uploader',
    )
with up_col2:
    st.write("")
    st.write("")
    template_bytes = make_template_pi_excel()
    st.download_button(
        "📥 Download Template",
        data=template_bytes,
        file_name="pi_template.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        key='pi_template_download',
    )

# ─────────────────────────────────────────────────────────────────────────────
# PROCESS UPLOAD
# ─────────────────────────────────────────────────────────────────────────────
file_changed = (
    uploaded is not None and
    (st.session_state.pi_uploaded_file_name != uploaded.name or
     st.session_state.pi_uploaded_file_size != uploaded.size or
     st.session_state.pi_analysis is None)
)

if file_changed:
    # Read file bytes ONCE for caching (read once, use everywhere)
    file_bytes = uploaded.getvalue()
    try:
        if uploaded.name.lower().endswith('.csv'):
            df_input = pd.read_csv(io.BytesIO(file_bytes))
        else:
            df_input = pd.read_excel(io.BytesIO(file_bytes))
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
                st.success(f"✅ Period: `{period_pair[0]}` ({p1_val}) vs `{period_pair[1]}` ({p2_val})")
            except Exception:
                st.warning(f"⚠️ Period cols ada tapi nilai tidak terbaca")
        else:
            st.error(f"❌ Period cols tidak ditemukan. Butuh: {PERIOD_PAIRS}")
            st.stop()

    with val_col2:
        # Required column check
        missing = [c for c in REQUIRED_COLS if c not in cols_in]
        if missing:
            st.error(f"❌ Missing kolom: `{missing}`")
            st.stop()
        else:
            st.success(f"✅ Semua {len(REQUIRED_COLS)} required columns OK")

    # Process button — FAST path now (cached compute, no Excel build yet)
    if st.button("🚀 Process Data", type="primary", key='pi_process'):
        with st.spinner("Running PI analysis (fast path)..."):
            try:
                result = cached_pi_compute(file_bytes, uploaded.name)
            except Exception as e:
                st.error(f"❌ Analyze error: {e}")
                st.exception(e)
                st.stop()

            st.session_state.pi_analysis = result
            st.session_state.pi_file_bytes = file_bytes  # for lazy Excel
            st.session_state.pi_uploaded_file_name = uploaded.name
            st.session_state.pi_uploaded_file_size = uploaded.size
            st.success(f"✅ Selesai! {len(result['df_enriched']):,} rows processed.")
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# MAIN DASHBOARD (only if analysis available)
# ═══════════════════════════════════════════════════════════════════════════
if st.session_state.pi_analysis is not None:
    result = st.session_state.pi_analysis
    df = result['df_enriched']
    overall = result['overall']
    segments = result['segments']
    contribs = result['contribs']
    period_p1 = result['period_p1']
    period_p2 = result['period_p2']

    # ─────────────────────────────────────────────────────────────────────────
    # HASIL ANALISIS HEADER
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown(f'<div class="section-header">📈 Hasil Analisis — {period_p1} vs {period_p2}</div>',
                unsafe_allow_html=True)
    st.markdown(f"📌 File: `{st.session_state.pi_uploaded_file_name}` · {len(df):,} SKU diproses")

    # ─────────────────────────────────────────────────────────────────────────
    # ZONE 2 — EXECUTIVE SUMMARY (KPI Cards)
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">2️⃣ Executive Summary</div>', unsafe_allow_html=True)

    # Compute KPIs
    pi_a = overall['A']
    pi_e = overall['E']
    pi_delta = overall['total']
    n_ex = overall['n_ex']
    n_dep = overall['n_dep']
    n_new = overall['n_new']

    # Margin avg cur
    ex_only = df[df['sku_type'] == 'Existing']
    avg_margin = ex_only['margin_pct_cur'].mean()

    # Framework triggers
    n_framework = int((df['framework_check'] == 'TRUE').sum())

    # COGS need improve (CI Group D + E in current)
    n_cogs_improve = int(df['ci_group_cur'].isin(['D.95-105', 'E.>105']).sum())

    # PI bucket distribution (Existing, cur)
    pi_above_110 = int(ex_only['pi_group_cur'].isin(['D.105-110', 'E.110-120', 'F.>120']).sum())
    pi_match = int(ex_only['pi_group_cur'].isin(['B.95-<100', 'C.100-105']).sum())
    pi_below_95 = int((ex_only['pi_group_cur'] == 'A.<95').sum())
    n_ex_total = len(ex_only) if len(ex_only) > 0 else 1

    # Row 1: PI / ΔPI / Avg Margin
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(kpi_card(
            "Avg PI Current (E)",
            fmt_pi(pi_e),
            delta=pi_delta,
            delta_label=fmt_pi_delta(pi_delta),
            sub=f"P1 (A): {fmt_pi(pi_a)}"
        ), unsafe_allow_html=True)
    with c2:
        # Total decomposition magnitude
        total_abs = abs(overall['eff_dep']) + abs(overall['eff_price']) + abs(overall['eff_comp']) + abs(overall['eff_new'])
        st.markdown(kpi_card(
            "Total Δ PI",
            fmt_pi_delta(pi_delta),
            sub=f"Sum |effects| = {total_abs:.3f}"
        ), unsafe_allow_html=True)
    with c3:
        st.markdown(kpi_card(
            "Avg Margin % (Existing, Cur)",
            fmt_pct(avg_margin) if pd.notna(avg_margin) else "—",
            sub="Average margin di SKU Existing"
        ), unsafe_allow_html=True)

    # Row 2: SKU counts
    c4, c5, c6 = st.columns(3)
    with c4:
        st.markdown(kpi_card(
            "# SKU Existing",
            fmt_count(n_ex),
            sub=f"Punya PI di P1 dan P2"
        ), unsafe_allow_html=True)
    with c5:
        st.markdown(kpi_card(
            "# SKU New",
            fmt_count(n_new),
            sub=f"Muncul di P2 only"
        ), unsafe_allow_html=True)
    with c6:
        st.markdown(kpi_card(
            "# SKU Departing",
            fmt_count(n_dep),
            sub=f"Ada di P1, hilang di P2"
        ), unsafe_allow_html=True)

    # Row 3: Action SKU counts
    c7, c8, c9 = st.columns(3)
    with c7:
        st.markdown(kpi_card(
            "🚨 Framework Triggered",
            fmt_count(n_framework),
            sub="SKU butuh repricing action"
        ), unsafe_allow_html=True)
    with c8:
        st.markdown(kpi_card(
            "⚠️ COGS Need Improve",
            fmt_count(n_cogs_improve),
            sub="CI Group D (95-105) atau E (>105)"
        ), unsafe_allow_html=True)
    with c9:
        st.markdown(kpi_card(
            "PI Distribution (Cur)",
            f"{pi_above_110/n_ex_total*100:.0f}% Above110 · {pi_match/n_ex_total*100:.0f}% Match",
            sub=f"Below95: {pi_below_95/n_ex_total*100:.0f}% · {n_ex_total:,} Existing"
        ), unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────────
    # ZONE 3 — PI DECOMPOSITION (Tornado + Tabel 1 + Tabel 2)
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">3️⃣ PI Decomposition (Shapley)</div>', unsafe_allow_html=True)

    # Narrative
    direction = "naik" if pi_delta > 0 else "turun"
    # Top driver
    drivers = [
        ('1. Churned SKU', overall['eff_dep']),
        ('2. Price Change Effect', overall['eff_price']),
        ('3. Comp Effect', overall['eff_comp']),
        ('4. New SKU', overall['eff_new']),
    ]
    top_driver = max(drivers, key=lambda x: abs(x[1]))
    st.markdown(f"""
    PI overall **{direction}** dari **{pi_a:.2f}** ke **{pi_e:.2f}** (Δ **{pi_delta:+.3f}**).
    Driver utama: **{top_driver[0]}** ({top_driver[1]:+.3f}).
    Comp effect breakdown — Normal: **{overall['eff_normal_comp']:+.3f}**, Blended (Discount): **{overall['eff_discount_comp']:+.3f}**.
    """)

    # Scope filter for tornado
    scope_t = st.radio(
        "Scope:",
        ['Overall', 'Dry', 'Fresh', 'Frozen'],
        horizontal=True,
        key='pi_zone3_scope'
    )
    if scope_t == 'Overall':
        decomp_for_chart = overall
    else:
        decomp_for_chart = segments[scope_t]

    fig_tornado = make_pi_tornado(decomp_for_chart, scope_label=scope_t)
    st.plotly_chart(fig_tornado, use_container_width=True)

    # Tabel 1: Per-segment decomposition
    st.markdown("##### 📊 Tabel 1: PI Decomposition per Segment")
    st.caption("Step-by-step PI movement per segment. Sum dari 5 effect = Total Δ (math identity exact via Shapley).")

    t1 = build_pi_decomp_table(overall, segments, contribs)
    seg_cols = ['Overall', 'Dry', 'Fresh', 'Frozen']
    # Format display
    def fmt_t1_row(row):
        label = row['Step']
        is_baseline = 'Baseline' in label or 'Result' in label
        out = {'Step': label}
        for c in seg_cols:
            v = row[c]
            if is_baseline:
                out[c] = f"{v:.4f}" if pd.notna(v) else "—"
            else:
                out[c] = f"{v:+.4f}" if pd.notna(v) else "—"
        return out
    t1_display = pd.DataFrame([fmt_t1_row(r) for _, r in t1.iterrows()])

    # Color the effect rows
    def style_t1(orig, disp):
        # Compute vmax from non-baseline rows
        effect_mask = ~orig['Step'].str.contains('Baseline|Result', regex=True)
        vals = orig.loc[effect_mask, seg_cols].values.flatten()
        vals = [v for v in vals if pd.notna(v)]
        vmax = max(abs(v) for v in vals) if vals else 1
        if vmax == 0: vmax = 1

        def apply_row(row):
            label = row['Step']
            is_baseline = ('Baseline' in label) or ('Result' in label)
            is_total = 'Total Δ' in label
            styles = []
            for col in disp.columns:
                if col == 'Step':
                    if is_baseline:
                        styles.append('background-color: #F3F4F6; font-weight: 700;')
                    elif is_total:
                        styles.append('background-color: #DBEAFE; font-weight: 700;')
                    elif label.startswith('    '):
                        styles.append('padding-left: 24px;')
                    else:
                        styles.append('')
                else:
                    if is_baseline:
                        styles.append('background-color: #F3F4F6; font-weight: 700;')
                    elif is_total:
                        v = orig.loc[row.name, col]
                        styles.append(gradient_color(v, vmax) + ' font-weight: 700;')
                    else:
                        v = orig.loc[row.name, col]
                        styles.append(gradient_color(v, vmax))
            return styles
        return disp.style.apply(apply_row, axis=1)

    st.dataframe(style_t1(t1, t1_display), use_container_width=True, hide_index=True)

    # Tabel 2: Per-segment contribution to OVERALL
    st.markdown("##### 📊 Tabel 2: Segment Contribution to Overall (Exact Math Identity)")
    st.caption("Σ Dry + Fresh + Frozen = Overall (exact, zero residual). Methodology: exact_contributions formula.")

    t2 = build_pi_contrib_table(overall, contribs)
    t2_cols = ['Dry contrib', 'Fresh contrib', 'Frozen contrib', 'Overall (sum)', 'Overall actual']

    def fmt_t2_row(row):
        out = {'Effect': row['Effect']}
        for c in t2_cols:
            out[c] = f"{row[c]:+.4f}" if pd.notna(row[c]) else "—"
        return out
    t2_display = pd.DataFrame([fmt_t2_row(r) for _, r in t2.iterrows()])

    def style_t2(orig, disp):
        vals = orig[t2_cols].values.flatten()
        vals = [v for v in vals if pd.notna(v)]
        vmax = max(abs(v) for v in vals) if vals else 1
        if vmax == 0: vmax = 1
        def apply_row(row):
            styles = []
            for col in disp.columns:
                if col in ('Effect',):
                    styles.append('')
                else:
                    v = orig.loc[row.name, col]
                    styles.append(gradient_color(v, vmax))
            return styles
        return disp.style.apply(apply_row, axis=1)

    st.dataframe(style_t2(t2, t2_display), use_container_width=True, hide_index=True)

    # ─────────────────────────────────────────────────────────────────────────
    # ZONE 4 — L1 CATEGORY BREAKDOWN
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">4️⃣ L1 Category Movement</div>', unsafe_allow_html=True)
    st.caption("PI movement per L1 category dengan 5-component decomposition.")

    l1_scope = st.radio(
        "Scope L1:",
        ['Overall', 'Dry', 'Fresh', 'Frozen'],
        horizontal=True,
        key='pi_l1_scope'
    )
    l1_table = build_l1_pi_table(df, scope=l1_scope)
    if l1_table.empty:
        st.info("Tidak ada data L1 untuk scope ini.")
    else:
        # Format columns
        l1_display = l1_table.copy()
        for c in ['Avg PI Prev (A)', 'Avg PI Cur (E)']:
            l1_display[c] = l1_display[c].apply(lambda v: f"{v:.2f}" if pd.notna(v) else "—")
        for c in ['Total Δ', '1. Churned Eff', '2. Price Eff', '3. Comp Price Eff',
                  '3.1 Normal Comp Eff', '3.2 Discount Comp Eff', '4. New SKU Eff']:
            l1_display[c] = l1_display[c].apply(lambda v: f"{v:+.3f}" if pd.notna(v) else "—")
        for c in ['n Existing', 'n Departing', 'n New']:
            l1_display[c] = l1_display[c].apply(lambda v: f"{int(v):,}" if pd.notna(v) else "—")

        # Gradient on effect columns
        effect_cols_l1 = ['Total Δ', '1. Churned Eff', '2. Price Eff', '3. Comp Price Eff',
                         '3.1 Normal Comp Eff', '3.2 Discount Comp Eff', '4. New SKU Eff']
        vals = l1_table[effect_cols_l1].values.flatten()
        vals = [v for v in vals if pd.notna(v)]
        vmax = max(abs(v) for v in vals) if vals else 1
        if vmax == 0: vmax = 1

        def apply_l1_style(row):
            styles = []
            for col in l1_display.columns:
                if col in effect_cols_l1:
                    v = l1_table.loc[row.name, col]
                    styles.append(gradient_color(v, vmax))
                else:
                    styles.append('')
            return styles

        st.markdown(f"**Scope: {l1_scope}** · {len(l1_display)} L1 categories (sorted by Total Δ desc)")
        st.dataframe(
            l1_display.style.apply(apply_l1_style, axis=1),
            use_container_width=True, hide_index=True, height=600
        )

    # ─────────────────────────────────────────────────────────────────────────
    # ZONE 5 — PRICE × COMP MATRIX
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">5️⃣ Price × Comp Direction Matrix</div>', unsafe_allow_html=True)
    st.caption("Behavior pattern: SKU yang harga naik/turun vs gerakan kompetitor. Existing SKU only.")

    matrix_scope = st.radio(
        "Scope Matrix:",
        ['Overall', 'Dry', 'Fresh', 'Frozen'],
        horizontal=True,
        key='pi_matrix_scope'
    )
    matrix_df, n_total = build_price_comp_matrix(df, scope=matrix_scope)
    if matrix_df is None:
        st.info("Tidak ada data Existing SKU untuk scope ini.")
    else:
        # Display matrix + percentage
        st.markdown(f"**Scope: {matrix_scope}** · Total {n_total:,} Existing SKU")

        # Count matrix
        m_count = matrix_df.copy()
        m_count['Total'] = m_count.sum(axis=1)
        m_count.loc['TOTAL'] = m_count.sum(axis=0)

        # Pct matrix
        m_pct = matrix_df / n_total * 100

        st.markdown("**Count (SKU):**")
        st.dataframe(m_count.style.format("{:,}"), use_container_width=True)

        st.markdown("**% of Total Existing:**")
        # Gradient coloring on pct
        max_p = m_pct.values.max()
        def color_pct(val):
            if pd.isna(val): return ''
            alpha = val / max_p if max_p > 0 else 0
            r = int(255 - (255-22) * alpha)
            g = int(255 - (255-163) * alpha)
            b = int(255 - (255-74) * alpha)
            return f'background-color: rgb({r},{g},{b}); color: #111827;'
        st.dataframe(
            m_pct.style.format("{:.1f}%").map(color_pct),
            use_container_width=True
        )

        # Diagonal vs off-diagonal insight
        diag_sum = sum(matrix_df.iloc[i, i] for i in range(3))
        st.caption(f"💡 Diagonal (Price follows Comp direction): **{diag_sum:,}** SKU "
                  f"({diag_sum/n_total*100:.1f}%). "
                  f"Off-diagonal = misaligned dengan kompetitor.")

    # ─────────────────────────────────────────────────────────────────────────
    # ZONE 6 — PI DISTRIBUTION
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">6️⃣ PI Distribution & Movement</div>', unsafe_allow_html=True)
    st.caption("Berapa SKU yang bergerak antar PI bucket. Existing SKU only.")

    dist_scope = st.radio(
        "Scope Distribution:",
        ['Overall', 'Dry', 'Fresh', 'Frozen'],
        horizontal=True,
        key='pi_dist_scope'
    )
    dist_df = build_pi_distribution(df, scope=dist_scope)
    if dist_df.empty:
        st.info("Tidak ada data Existing untuk scope ini.")
    else:
        # Bar chart side-by-side Prev vs Cur
        fig_dist = go.Figure()
        fig_dist.add_trace(go.Bar(
            name='Prev',
            x=dist_df['PI Bucket'],
            y=dist_df['n Prev'],
            marker_color='#9CA3AF',
            text=dist_df['n Prev'].apply(lambda v: f"{int(v):,}"),
            textposition='outside',
        ))
        fig_dist.add_trace(go.Bar(
            name='Cur',
            x=dist_df['PI Bucket'],
            y=dist_df['n Cur'],
            marker_color='#2563EB',
            text=dist_df['n Cur'].apply(lambda v: f"{int(v):,}"),
            textposition='outside',
        ))
        fig_dist.update_layout(
            title=f"PI Bucket Distribution — {dist_scope}",
            barmode='group',
            height=400,
            plot_bgcolor='white',
            margin=dict(t=60, b=40, l=40, r=20),
        )
        fig_dist.update_yaxes(showgrid=True, gridcolor='#F3F4F6')
        st.plotly_chart(fig_dist, use_container_width=True)

        # Distribution table with delta
        dist_disp = dist_df.copy()
        dist_disp['n Prev']  = dist_disp['n Prev'].apply(lambda v: f"{int(v):,}")
        dist_disp['n Cur']   = dist_disp['n Cur'].apply(lambda v: f"{int(v):,}")
        dist_disp['Δ Count'] = dist_disp['Δ Count'].apply(lambda v: f"{v:+,}")
        dist_disp['% Prev']  = dist_disp['% Prev'].apply(lambda v: f"{v*100:.1f}%")
        dist_disp['% Cur']   = dist_disp['% Cur'].apply(lambda v: f"{v*100:.1f}%")
        dist_disp['Δ %']     = dist_disp['Δ %'].apply(lambda v: f"{v*100:+.1f}%")
        st.dataframe(dist_disp, use_container_width=True, hide_index=True)

    # ─────────────────────────────────────────────────────────────────────────
    # ZONE 7 — TOP MOVERS SKU
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">7️⃣ Top Movers SKU (by Δ PI)</div>', unsafe_allow_html=True)
    st.caption("Top 30 SKU dengan PI movement terbesar (gainers ↑ = PI naik = harga makin mahal vs comp). "
               "Existing SKU only.")

    gainers, losers = build_top_movers_pi(df, n=30)

    mv_col1, mv_col2 = st.columns(2)
    fmt_mover = {
        'Δ PI': '{:+.2f}',
        'Price Eff': '{:+.3f}',
        'Comp Price Eff': '{:+.3f}',
        'Normal Comp Eff': '{:+.3f}',
        'Discount Comp Eff': '{:+.3f}',
        'Price Δ%': '{:+.2%}',
        'COGS Δ%': '{:+.2%}',
    }

    with mv_col1:
        st.markdown("**🔼 Top 30 PI Gainers (PI naik)**")
        if gainers.empty:
            st.info("Tidak ada data.")
        else:
            gdf = pd.DataFrame([fmt_mover_row(r, i+1) for i, (_, r) in enumerate(gainers.iterrows())])
            st.dataframe(
                gdf.style.format(fmt_mover),
                use_container_width=True, hide_index=True, height=600
            )

    with mv_col2:
        st.markdown("**🔽 Top 30 PI Losers (PI turun)**")
        if losers.empty:
            st.info("Tidak ada data.")
        else:
            ldf = pd.DataFrame([fmt_mover_row(r, i+1) for i, (_, r) in enumerate(losers.iterrows())])
            st.dataframe(
                ldf.style.format(fmt_mover),
                use_container_width=True, hide_index=True, height=600
            )

    # ─────────────────────────────────────────────────────────────────────────
    # ZONE 8 — PI DISTRIBUTION (alt visual already in Zone 6)
    # We use this slot for: STRUCTURAL LOSS + COGS NEED IMPROVE
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">8️⃣ Quadrant Analysis (PI × Margin × CI)</div>', unsafe_allow_html=True)
    st.caption("Cross-tables untuk identify SKU clusters yang misaligned.")

    quad_tabs = st.tabs(["PI vs Margin", "COGS Index vs PI", "COGS Index vs Margin"])

    ex_only_q = df[df['sku_type'] == 'Existing']

    with quad_tabs[0]:
        # PI bucket × Margin bucket count matrix
        if 'pi_group_cur' in ex_only_q.columns and 'margin_group_cur' in ex_only_q.columns:
            cross1 = pd.crosstab(
                ex_only_q['pi_group_cur'],
                ex_only_q['margin_group_cur']
            ).reindex(index=PI_BINS_LBL, columns=MG_BINS_LBL, fill_value=0)
            st.markdown(f"**Count of Existing SKU** by PI Bucket (rows) × Margin Bucket (cols)")
            max_v = cross1.values.max() if cross1.values.size > 0 else 1
            def color_count(val):
                if pd.isna(val) or val == 0: return ''
                alpha = val / max_v if max_v > 0 else 0
                alpha = min(1.0, alpha)
                r = int(255 - (255-22) * alpha)
                g = int(255 - (255-163) * alpha)
                b = int(255 - (255-74) * alpha)
                return f'background-color: rgb({r},{g},{b}); color: #111827;'
            st.dataframe(cross1.style.format("{:,}").map(color_count), use_container_width=True)
            st.caption("💡 SKU at high PI + low Margin = double whammy (uncompetitive + low profit). "
                      "Low PI + high Margin = good underpriced position (room to test price up).")

    with quad_tabs[1]:
        if 'ci_group_cur' in ex_only_q.columns and 'pi_group_cur' in ex_only_q.columns:
            cross2 = pd.crosstab(
                ex_only_q['ci_group_cur'],
                ex_only_q['pi_group_cur']
            ).reindex(index=CI_BINS_LBL, columns=PI_BINS_LBL, fill_value=0)
            st.markdown(f"**Count of Existing SKU** by COGS Index (rows) × PI Bucket (cols)")
            max_v = cross2.values.max() if cross2.values.size > 0 else 1
            def color_count2(val):
                if pd.isna(val) or val == 0: return ''
                alpha = val / max_v if max_v > 0 else 0
                alpha = min(1.0, alpha)
                r = int(255 - (255-22) * alpha)
                g = int(255 - (255-163) * alpha)
                b = int(255 - (255-74) * alpha)
                return f'background-color: rgb({r},{g},{b}); color: #111827;'
            st.dataframe(cross2.style.format("{:,}").map(color_count2), use_container_width=True)
            st.caption("💡 High CI (D/E) + High PI = structurally over-priced (cost lebih mahal dari comp + jual lebih mahal). "
                      "Vendor negotiation needed.")

    with quad_tabs[2]:
        if 'ci_group_cur' in ex_only_q.columns and 'margin_group_cur' in ex_only_q.columns:
            cross3 = pd.crosstab(
                ex_only_q['ci_group_cur'],
                ex_only_q['margin_group_cur']
            ).reindex(index=CI_BINS_LBL, columns=MG_BINS_LBL, fill_value=0)
            st.markdown(f"**Count of Existing SKU** by COGS Index (rows) × Margin Bucket (cols)")
            max_v = cross3.values.max() if cross3.values.size > 0 else 1
            def color_count3(val):
                if pd.isna(val) or val == 0: return ''
                alpha = val / max_v if max_v > 0 else 0
                alpha = min(1.0, alpha)
                r = int(255 - (255-22) * alpha)
                g = int(255 - (255-163) * alpha)
                b = int(255 - (255-74) * alpha)
                return f'background-color: rgb({r},{g},{b}); color: #111827;'
            st.dataframe(cross3.style.format("{:,}").map(color_count3), use_container_width=True)
            st.caption("💡 High CI (D/E) + Low Margin = structural loss (cost mahal + margin tipis).")

    # ─────────────────────────────────────────────────────────────────────────
    # ZONE 9 — FRAMEWORK CHECK
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">9️⃣ Framework Check — Actionable SKU List</div>',
                unsafe_allow_html=True)
    st.caption("SKU yang trigger business rules untuk repricing. Definisi 5 rules: lihat caption per row.")

    fc_df = build_framework_check_table(df)
    if fc_df.empty:
        st.info("✅ Tidak ada SKU yang trigger framework rules.")
    else:
        # Summary by rule
        rule_summary = fc_df['Rule'].value_counts().reset_index()
        rule_summary.columns = ['Rule', 'Count']
        st.markdown(f"**Total {len(fc_df)} SKU trigger framework. Breakdown:**")
        st.dataframe(rule_summary, hide_index=True, use_container_width=True)

        st.markdown("**Detail SKU:**")
        fc_disp = fc_df.copy()
        if 'pi' in fc_disp.columns:
            fc_disp['pi'] = fc_disp['pi'].apply(lambda v: f"{v:.1f}" if pd.notna(v) else "—")
            fc_disp['next_pi'] = fc_disp['next_pi'].apply(lambda v: f"{v:.1f}" if pd.notna(v) else "—")
            fc_disp['diff_pi'] = fc_disp['diff_pi'].apply(lambda v: f"{v:+.2f}" if pd.notna(v) else "—")
        for c in ['margin_pct_prev', 'margin_pct_cur']:
            if c in fc_disp.columns:
                fc_disp[c] = fc_disp[c].apply(lambda v: f"{v*100:.1f}%" if pd.notna(v) else "—")
        for c in ['price', 'next_price', 'cogs', 'next_cogs', 'comp_price', 'next_comp_price']:
            if c in fc_disp.columns:
                fc_disp[c] = fc_disp[c].apply(lambda v: f"{v:,.0f}" if pd.notna(v) else "—")
        st.dataframe(fc_disp, use_container_width=True, hide_index=True, height=500)

    # ─────────────────────────────────────────────────────────────────────────
    # ZONE 10 — STRUCTURAL LOSS + COGS NEED IMPROVE
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">🔟 Structural Loss & COGS Need Improve</div>',
                unsafe_allow_html=True)
    st.caption("L1 categories dengan banyak SKU di CI Group D/E (cost mahal vs comp) — procurement action needed.")

    sl_col1, sl_col2 = st.columns(2)

    with sl_col1:
        st.markdown("##### 📋 Structural Loss by L1 Category")
        sl_df = build_structural_loss(df)
        if sl_df.empty:
            st.info("Tidak ada L1 di CI Group D/E.")
        else:
            sl_disp = sl_df.copy()
            sl_disp['% of Category'] = sl_disp['% of Category'].apply(lambda v: f"{v*100:.1f}%")
            sl_disp['Avg COGS Index'] = sl_disp['Avg COGS Index'].apply(lambda v: f"{v:.1f}")
            sl_disp['Avg Margin %'] = sl_disp['Avg Margin %'].apply(lambda v: f"{v*100:.1f}%")
            sl_disp['Avg PI (Cur)'] = sl_disp['Avg PI (Cur)'].apply(lambda v: f"{v:.1f}")
            sl_disp['n SKU'] = sl_disp['n SKU'].apply(lambda v: f"{v:,}")
            st.dataframe(sl_disp, use_container_width=True, hide_index=True, height=400)

    with sl_col2:
        st.markdown("##### 📋 COGS Need Improve — SKU List Summary")
        ci_df = build_cogs_need_improve(df)
        if ci_df.empty:
            st.info("Tidak ada SKU di CI D/E.")
        else:
            # Show count by L1 + BL
            ci_summary = ci_df.groupby(['pricing_bl_25', 'l1_category_name']).size().reset_index()
            ci_summary.columns = ['BL', 'L1', 'n SKU']
            ci_summary = ci_summary.sort_values('n SKU', ascending=False).head(20)
            ci_summary['n SKU'] = ci_summary['n SKU'].apply(lambda v: f"{v:,}")
            st.markdown(f"**Total {len(ci_df):,} SKU need COGS improvement. Top 20 L1:**")
            st.dataframe(ci_summary, use_container_width=True, hide_index=True, height=400)

    # ─────────────────────────────────────────────────────────────────────────
    # ZONE 11 — PARETO CLASS MOVEMENT
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">1️⃣1️⃣ Pareto Class Movement</div>', unsafe_allow_html=True)
    st.caption("PI movement per Pareto class (A/B/C) — strategic view by SKU importance.")

    pareto_scope = st.radio(
        "Scope Pareto:",
        ['Overall', 'Dry', 'Fresh', 'Frozen'],
        horizontal=True,
        key='pi_pareto_scope'
    )
    pareto_table = build_pareto_pi_table(df, scope=pareto_scope)
    if pareto_table.empty:
        st.info("Tidak ada data Pareto.")
    else:
        pareto_display = pareto_table.copy()
        for c in ['Avg PI Prev (A)', 'Avg PI Cur (E)']:
            pareto_display[c] = pareto_display[c].apply(lambda v: f"{v:.2f}" if pd.notna(v) else "—")
        for c in ['Total Δ', '1. Churned Eff', '2. Price Eff', '3. Comp Price Eff',
                  '3.1 Normal Comp Eff', '3.2 Discount Comp Eff', '4. New SKU Eff']:
            pareto_display[c] = pareto_display[c].apply(lambda v: f"{v:+.3f}" if pd.notna(v) else "—")
        for c in ['n Existing', 'n Departing', 'n New']:
            pareto_display[c] = pareto_display[c].apply(lambda v: f"{int(v):,}" if pd.notna(v) else "—")

        effect_cols_p = ['Total Δ', '1. Churned Eff', '2. Price Eff', '3. Comp Price Eff',
                        '3.1 Normal Comp Eff', '3.2 Discount Comp Eff', '4. New SKU Eff']
        vals = pareto_table[effect_cols_p].values.flatten()
        vals = [v for v in vals if pd.notna(v)]
        vmax = max(abs(v) for v in vals) if vals else 1
        if vmax == 0: vmax = 1

        def apply_pareto_style(row):
            styles = []
            for col in pareto_display.columns:
                if col in effect_cols_p:
                    v = pareto_table.loc[row.name, col]
                    styles.append(gradient_color(v, vmax))
                else:
                    styles.append('')
            return styles

        st.dataframe(
            pareto_display.style.apply(apply_pareto_style, axis=1),
            use_container_width=True, hide_index=True
        )

    # ─────────────────────────────────────────────────────────────────────────
    # DOWNLOAD EXCEL (LAZY — only build when user clicks)
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">📥 Download Full Report</div>', unsafe_allow_html=True)
    st.caption("Download complete 13-sheet Excel report (sama persis output script pi_analyzer_v1.py). "
               "Build Excel akan butuh ~50-60 detik karena ada styling per-cell. Klik tombol di bawah saat lo butuh.")

    out_name = f"PI_Analysis_{result['period_type']}_{period_p1}_vs_{period_p2}.xlsx"

    # Lazy generation: only build Excel when user clicks "Prepare Excel"
    if 'pi_excel_ready' not in st.session_state:
        st.session_state.pi_excel_ready = False

    if not st.session_state.pi_excel_ready:
        if st.button("🔨 Build Excel Report (~60s)", type="primary", key='pi_excel_prepare'):
            with st.spinner("Building 13-sheet Excel workbook... ini bisa makan ~60 detik."):
                try:
                    excel_bytes = cached_pi_excel_bytes(
                        st.session_state.pi_file_bytes,
                        st.session_state.pi_uploaded_file_name
                    )
                    st.session_state.pi_excel_bytes = excel_bytes
                    st.session_state.pi_excel_ready = True
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Excel build error: {e}")
                    st.exception(e)
    else:
        st.success("✅ Excel report ready. Click below to download.")
        st.download_button(
            "📥 Download Excel (13 sheets)",
            data=st.session_state.pi_excel_bytes,
            file_name=out_name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=False,
            key='pi_excel_download'
        )
        if st.button("🔄 Rebuild Excel", type="secondary", key='pi_excel_rebuild'):
            st.session_state.pi_excel_ready = False
            if 'pi_excel_bytes' in st.session_state:
                del st.session_state.pi_excel_bytes
            st.rerun()

else:
    st.info("⬆️ Upload file PI raw data untuk mulai analisis. Format mengikuti `pi_analyzer_v1.py`.")
