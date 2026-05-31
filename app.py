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
    initial_sidebar_state="collapsed",
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

def make_waterfall_chart(pvm, scope='TOTAL', mode='rp'):
    """
    Build waterfall chart.
    scope: 'TOTAL', 'Dry', 'Fresh', 'Frozen', 'PL'
    mode: 'rp' (Rupiah) or 'pp' (margin points)
    """
    d = pvm[scope]
    if mode == 'rp':
        gp_start = d['gp_start']
        churned = -d['gp_dep']
        cogs = d['cogs_rp']
        price = d['price_rp']
        volmix = d['volmix_rp']
        new = d['gp_new']
        gp_end = d['gp_end']
        existing = cogs + price + volmix
        unit = "Rp"
        fmt_func = lambda v: fmt_rp(v)
    else:  # pp
        gp_start = d['m_base'] * 100
        churned = d['pp_B'] * 100
        cogs = d['pp_cogs'] * 100
        price = d['pp_price'] * 100
        volmix = d['pp_volmix'] * 100
        new = d['pp_G'] * 100
        gp_end = d['m_end'] * 100
        existing = cogs + price + volmix
        unit = "pp"
        fmt_func = lambda v: f"{v:+.3f}pp" if v != gp_start and v != gp_end else f"{v:.2f}%"

    # Build waterfall with sub-bars for Existing breakdown
    labels = [
        f"GP P1" if mode=='rp' else 'Margin P1',
        '1. Churned SKU Effect',
        '  2.1 COGS Effect',
        '  2.2 Price Effect',
        '  2.3 Vol/Mix Effect',
        '3. New SKU Effect',
        f"GP P2" if mode=='rp' else 'Margin P2',
    ]
    measure = ['absolute', 'relative', 'relative', 'relative', 'relative', 'relative', 'total']
    values = [gp_start, churned, cogs, price, volmix, new, gp_end]

    if mode == 'rp':
        text_vals = [fmt_rp(gp_start), fmt_rp(churned), fmt_rp(cogs),
                     fmt_rp(price), fmt_rp(volmix), fmt_rp(new), fmt_rp(gp_end)]
    else:
        text_vals = [f"{gp_start:.2f}%", f"{churned:+.3f}pp", f"{cogs:+.3f}pp",
                     f"{price:+.3f}pp", f"{volmix:+.3f}pp", f"{new:+.3f}pp",
                     f"{gp_end:.2f}%"]

    fig = go.Figure(go.Waterfall(
        name="Bridge",
        orientation="v",
        measure=measure,
        x=labels,
        y=values,
        text=text_vals,
        textposition="outside",
        connector={"line": {"color": "#9CA3AF", "dash": "dot"}},
        decreasing={"marker": {"color": "#DC2626"}},
        increasing={"marker": {"color": "#059669"}},
        totals={"marker": {"color": "#1F2937"}},
    ))

    # Add a subtle existing SKU effect annotation bracket
    existing_str = fmt_rp(existing) if mode == 'rp' else f"{existing:+.3f}pp"
    fig.update_layout(
        title=f"Margin Bridge — {scope} ({unit})  |  2. Existing SKU Effect = {existing_str}",
        showlegend=False,
        height=480,
        margin=dict(l=20, r=20, t=60, b=80),
        yaxis_title=unit,
        plot_bgcolor='white',
        xaxis=dict(tickangle=-15),
    )
    fig.update_yaxes(showgrid=True, gridcolor='#F3F4F6')
    return fig

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

def compute_top_movers(df, n=10):
    """Top n gainers + losers by gp_diff. Only Existing SKU (not New/Deprecated)."""
    if 'sku_status' in df.columns:
        existing = df[df['sku_status'] == 'Existing'].copy()
    else:
        existing = df.copy()
    existing = existing.dropna(subset=['gp_diff'])

    gainers = existing.nlargest(n, 'gp_diff')
    losers = existing.nsmallest(n, 'gp_diff')
    return gainers, losers

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
if 'analysis' not in st.session_state:
    st.session_state.analysis = None
if 'uploaded_file_name' not in st.session_state:
    st.session_state.uploaded_file_name = None
if 'uploaded_file_size' not in st.session_state:
    st.session_state.uploaded_file_size = None

# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────
col_title, col_clear = st.columns([5, 1])
with col_title:
    st.title("📊 PVM Analyzer")
    st.caption("Pricing × Volume × Mix Decomposition — Astro Pricing Strategy")
with col_clear:
    st.write("")
    if st.session_state.analysis is not None:
        if st.button("🗑️ Clear data", type="secondary", use_container_width=True):
            st.session_state.analysis = None
            st.session_state.uploaded_file_name = None
            st.session_state.uploaded_file_size = None
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
    (st.session_state.uploaded_file_name != uploaded.name or
     st.session_state.uploaded_file_size != uploaded.size or
     st.session_state.analysis is None)
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
                st.session_state.analysis = result
                st.session_state.uploaded_file_name = uploaded.name
                st.session_state.uploaded_file_size = uploaded.size
                st.success(f"✅ Data processed: {result['meta']['n_rows']:,} rows enriched")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Processing error: {e}")
                import traceback
                st.code(traceback.format_exc())

# ─────────────────────────────────────────────────────────────────────────────
# ANALYSIS DISPLAY (only if data is processed)
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state.analysis is not None:
    A = st.session_state.analysis
    df = A['df']
    pvm = A['pvm']
    p1, p2 = A['p1'], A['p2']
    TOT = pvm['TOTAL']

    st.markdown(f'<div class="section-header">📈 Hasil Analisis — {p1} vs {p2}</div>', unsafe_allow_html=True)
    st.caption(f"📌 File: `{st.session_state.uploaded_file_name}` · {A['meta']['n_rows']:,} SKU diproses")

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

    # SKU counts
    if 'sku_status' in df.columns:
        n_existing = (df['sku_status'] == 'Existing').sum()
        n_new = (df['sku_status'] == 'New').sum()
        n_dep = (df['sku_status'] == 'Deprecated').sum()
        n_active_p2 = n_existing + n_new
    else:
        n_existing = n_new = n_dep = n_active_p2 = 0

    # Qty (existing only, since New/Dep skew comparison)
    qty_p1_total = df[df['sku_status'] == 'Existing']['qty_p1'].sum() if 'sku_status' in df.columns else df['qty_p1'].sum()
    qty_p2_total = df[df['sku_status'] == 'Existing']['qty_p2'].sum() if 'sku_status' in df.columns else df['qty_p2'].sum()
    qty_diff = qty_p2_total - qty_p1_total
    qty_diff_pct = qty_diff / qty_p1_total if qty_p1_total else 0

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

    # Row 2: Qty / SKU Active / SKU Churn
    c4, c5, c6 = st.columns(3)
    with c4:
        st.markdown(kpi_card(
            "Qty Sold (Existing SKU)",
            f"{qty_p2_total/1e6:.2f} M",
            delta=qty_diff_pct,
            delta_label=f"{qty_diff:+,.0f} ({qty_diff_pct*100:+.2f}%)",
            sub=f"P1: {qty_p1_total/1e6:.2f} M"
        ), unsafe_allow_html=True)
    with c5:
        st.markdown(kpi_card(
            "# SKU Active P2",
            f"{n_active_p2:,}",
            sub=f"Existing: {n_existing:,} · Net change vs P1"
        ), unsafe_allow_html=True)
    with c6:
        st.markdown(kpi_card(
            "SKU Churn",
            f"+{n_new:,} / -{n_dep:,}",
            sub=f"Net: {n_new - n_dep:+,} (New − Deprecated)"
        ), unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────
    # ZONE 3 — MARGIN BRIDGE WATERFALL
    # ─────────────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">3️⃣ Margin Bridge</div>', unsafe_allow_html=True)

    # Narrative
    pp_existing_tot = TOT['pp_cogs'] + TOT['pp_price'] + TOT['pp_volmix']
    pp_total = TOT['pp_total']
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
        Driver utama: {drivers_txt}.
        Existing SKU Effect = COGS + Price + Vol/Mix = **{fmt_pp(pp_existing_tot, 3)}**.
    """)

    # Scope toggle + mode toggle
    bx1, bx2 = st.columns([2, 1])
    with bx1:
        scope = st.radio(
            "Scope:",
            ['TOTAL', 'Dry', 'Fresh', 'Frozen', 'PL'],
            horizontal=True,
            key='waterfall_scope',
        )
    with bx2:
        mode = st.radio("Unit:", ['Rupiah (Rp)', 'Margin (pp)'], horizontal=True, key='waterfall_mode')
        mode_key = 'rp' if 'Rupiah' in mode else 'pp'

    fig = make_waterfall_chart(pvm, scope=scope, mode=mode_key)
    st.plotly_chart(fig, use_container_width=True)

    # Per-BL contribution table below waterfall
    with st.expander("📋 Breakdown numerical (semua BL)", expanded=False):
        bridge_data = []
        for bl in ['TOTAL'] + BL_ORDER:
            d = pvm[bl]
            existing_rp = d['cogs_rp'] + d['price_rp'] + d['volmix_rp']
            pp_existing = d['pp_cogs'] + d['pp_price'] + d['pp_volmix']
            bridge_data.append({
                'Scope': bl,
                'GP P1': d['gp_start'],
                'GP P2': d['gp_end'],
                'GP Δ': d['gp_end'] - d['gp_start'],
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
                'GP P1': '{:,.0f}', 'GP P2': '{:,.0f}', 'GP Δ': '{:,.0f}',
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

    # ─────────────────────────────────────────────────────────────────────
    # ZONE 4.5 — TOP MOVERS
    # ─────────────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">🔝 Top Movers (Existing SKU only)</div>', unsafe_allow_html=True)
    st.caption("Top 10 gainers & losers by GP change. Field driver kosong untuk diisi manual sesuai konteks bisnis.")

    gainers, losers = compute_top_movers(df, n=10)

    mv_col1, mv_col2 = st.columns(2)

    name_col = 'product_name' if 'product_name' in df.columns else ('sku_name' if 'sku_name' in df.columns else None)
    id_col = 'product_id' if 'product_id' in df.columns else ('sku_id' if 'sku_id' in df.columns else None)

    def mover_table(d, kind='gain'):
        rows = []
        for i, (_, r) in enumerate(d.iterrows(), 1):
            name = r.get(name_col, '—') if name_col else '—'
            bl = r.get('pricing_bl', '—')
            l1 = r.get('l1_category', '—')
            gp_d = r.get('gp_diff', 0)
            qty_pct = r.get('qty_diff_pct', np.nan)
            price_s = r.get('price_status', '—') or '—'
            cogs_s = r.get('cogs_status', '—') or '—'
            comp_s = r.get('comp_status', '—') or '—'
            pi_p1 = r.get('pi_p1', np.nan)
            pi_p2 = r.get('pi_p2', np.nan)
            pi_txt = f"{pi_p1:.0f}→{pi_p2:.0f}" if pd.notna(pi_p1) and pd.notna(pi_p2) else "—"
            rows.append({
                '#': i,
                'Product': str(name)[:40],
                'BL': bl, 'L1': l1,
                'GP Δ': gp_d,
                'Qty Δ%': qty_pct,
                'Price': price_s, 'COGS': cogs_s, 'Comp': comp_s,
                'PI': pi_txt,
                'Driver (isi manual)': '',
            })
        return pd.DataFrame(rows)

    with mv_col1:
        st.markdown("**🟢 Top 10 GP Gainers**")
        gdf = mover_table(gainers, 'gain')
        st.dataframe(
            gdf.style.format({'GP Δ': '{:+,.0f}', 'Qty Δ%': '{:+.1%}'}),
            use_container_width=True, hide_index=True, height=410
        )
    with mv_col2:
        st.markdown("**🔴 Top 10 GP Losers**")
        ldf = mover_table(losers, 'loss')
        st.dataframe(
            ldf.style.format({'GP Δ': '{:+,.0f}', 'Qty Δ%': '{:+.1%}'}),
            use_container_width=True, hide_index=True, height=410
        )

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
