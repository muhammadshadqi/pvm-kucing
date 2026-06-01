"""
Price Simulator — Page 3 (Astro Pricing Toolkit)
Simulate price scenario impact on GV, GP, Margin, and PI per SKU.

Two scenario sources supported:
1. Upload File 2 (standard format: product_id, baseline, var_1, var_2, ...)
2. Manual builder (search SKU, multi-select, dynamic variants)

Author: Shadqi (Pricing Strategy Analyst, Astro)
"""
import io
import os
import sys
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# ─────────────────────────────────────────────────────────────────────────────
# IMPORTS
# ─────────────────────────────────────────────────────────────────────────────
_PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PARENT_DIR not in sys.path:
    sys.path.insert(0, _PARENT_DIR)

from simulator import (compute as sim_compute, generate_excel as sim_generate_excel,
                       compute_overall_impact, REQUIRED_MASTER_COLS)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Price Simulator — Astro Pricing",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="auto",
)

st.markdown("""
<style>
    .main > div { padding-top: 1rem; }
    .section-header {
        font-size: 22px;
        font-weight: 700;
        color: #111827;
        margin-top: 32px;
        margin-bottom: 12px;
        padding-bottom: 8px;
        border-bottom: 2px solid #E5E7EB;
    }
    .kpi-card {
        border: 1px solid #E5E7EB;
        border-radius: 10px;
        padding: 14px;
        background: #FFFFFF;
        margin-bottom: 8px;
    }
    .kpi-card-label {
        font-size: 11px;
        color: #6B7280;
        font-weight: 700;
        text-transform: uppercase;
        margin-bottom: 4px;
    }
    .kpi-card-value {
        font-size: 24px;
        font-weight: 800;
        color: #111827;
    }
    .kpi-card-delta {
        font-size: 12px;
        font-weight: 600;
        margin-top: 2px;
    }
    .kpi-card-sub {
        font-size: 11px;
        color: #6B7280;
        margin-top: 2px;
    }
    .delta-pos { color: #16A34A; }
    .delta-neg { color: #DC2626; }
    .delta-neu { color: #6B7280; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# CACHED COMPUTE
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False, max_entries=3)
def cached_sim_compute(master_bytes, master_name, scenario_bytes, scenario_name):
    """Cache full sim by hash of both file bytes."""
    if master_name.lower().endswith('.csv'):
        df_master = pd.read_csv(io.BytesIO(master_bytes))
    else:
        df_master = pd.read_excel(io.BytesIO(master_bytes))

    if scenario_name.lower().endswith('.csv'):
        df_scenario = pd.read_csv(io.BytesIO(scenario_bytes))
    else:
        df_scenario = pd.read_excel(io.BytesIO(scenario_bytes))

    return sim_compute(df_master, df_scenario)


@st.cache_data(show_spinner=False, max_entries=2)
def cached_sim_excel(master_bytes, master_name, scenario_bytes, scenario_name):
    """Cache Excel generation."""
    result = cached_sim_compute(master_bytes, master_name, scenario_bytes, scenario_name)
    return sim_generate_excel(result)


# ─────────────────────────────────────────────────────────────────────────────
# UI HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def kpi_card(label, value, delta=None, delta_label=None, sub=None, delta_inverse=False):
    cls = "delta-neu"
    if delta is not None and pd.notna(delta):
        if delta > 0:
            cls = "delta-neg" if delta_inverse else "delta-pos"
            arrow = "▲"
        elif delta < 0:
            cls = "delta-pos" if delta_inverse else "delta-neg"
            arrow = "▼"
        else:
            arrow = "→"
            cls = "delta-neu"
    else:
        arrow = ""

    delta_html = ""
    if delta_label:
        delta_html = f'<div class="kpi-card-delta {cls}">{arrow} {delta_label}</div>'
    sub_html = f'<div class="kpi-card-sub">{sub}</div>' if sub else ""
    return f"""<div class="kpi-card">
<div class="kpi-card-label">{label}</div>
<div class="kpi-card-value">{value}</div>
{delta_html}
{sub_html}
</div>"""


def fmt_money(v):
    """Format Rupiah money in human-readable scale."""
    if pd.isna(v) or v is None:
        return "—"
    if abs(v) >= 1e12:
        return f"{v/1e12:.2f} T"
    if abs(v) >= 1e9:
        return f"{v/1e9:.2f} B"
    if abs(v) >= 1e6:
        return f"{v/1e6:.1f} M"
    if abs(v) >= 1e3:
        return f"{v/1e3:.1f} K"
    return f"{v:.0f}"


def fmt_money_delta(v):
    if pd.isna(v) or v is None:
        return "—"
    sign = '+' if v >= 0 else ''
    if abs(v) >= 1e9:
        return f"{sign}{v/1e9:.2f} B"
    if abs(v) >= 1e6:
        return f"{sign}{v/1e6:.1f} M"
    if abs(v) >= 1e3:
        return f"{sign}{v/1e3:.1f} K"
    return f"{sign}{v:.0f}"


def fmt_pct(v):
    if pd.isna(v) or v is None:
        return "—"
    return f"{v*100:.1f}%"


def fmt_pct_delta(v):
    if pd.isna(v) or v is None:
        return "—"
    return f"{v*100:+.2f} pp"


def fmt_pi(v):
    if pd.isna(v) or v is None:
        return "—"
    return f"{v:.1f}"


def fmt_pi_detail(v):
    if pd.isna(v) or v is None:
        return "—"
    return f"{v:.3f}"


def fmt_pi_delta(v):
    if pd.isna(v) or v is None:
        return "—"
    return f"{v:+.2f}"


# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
if 'sim_master_bytes' not in st.session_state:
    st.session_state.sim_master_bytes = None
if 'sim_master_name' not in st.session_state:
    st.session_state.sim_master_name = None
if 'sim_scenario_bytes' not in st.session_state:
    st.session_state.sim_scenario_bytes = None
if 'sim_scenario_name' not in st.session_state:
    st.session_state.sim_scenario_name = None
if 'sim_result' not in st.session_state:
    st.session_state.sim_result = None
if 'sim_excel_ready' not in st.session_state:
    st.session_state.sim_excel_ready = False
if 'sim_manual_scenarios' not in st.session_state:
    # Manual builder state: dict of product_id -> {baseline, var_1, var_2, ...}
    st.session_state.sim_manual_scenarios = {}
if 'sim_manual_variant_count' not in st.session_state:
    st.session_state.sim_manual_variant_count = 2
if 'sim_loaded_file2_name' not in st.session_state:
    st.session_state.sim_loaded_file2_name = None
if 'sim_overall' not in st.session_state:
    st.session_state.sim_overall = None


# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────
col_title, col_clear = st.columns([5, 1])
with col_title:
    st.title("⚖️ Price Simulator")
    st.caption("What-if Price Scenarios — Astro Pricing Strategy")
with col_clear:
    st.write("")
    if st.session_state.sim_result is not None:
        if st.button("🗑️ Clear all", type="secondary", use_container_width=True):
            for k in ['sim_master_bytes', 'sim_master_name', 'sim_scenario_bytes',
                      'sim_scenario_name', 'sim_result', 'sim_excel_ready', 'sim_excel_bytes']:
                if k in st.session_state:
                    st.session_state[k] = None if k != 'sim_excel_ready' else False
            st.session_state.sim_manual_scenarios = {}
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# ZONE 1A — UPLOAD MASTER DATA
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">1️⃣ Upload Master Data (Query 3 output)</div>', unsafe_allow_html=True)

uploaded_master = st.file_uploader(
    "File 1 — Master Data (output Query 3 di Page 4)",
    type=['xlsx', 'xls', 'csv'],
    help=f"Format CSV/Excel dengan kolom: {', '.join(REQUIRED_MASTER_COLS)}",
    key='sim_master_upload'
)

# Process master file
df_master = None
if uploaded_master is not None:
    try:
        master_bytes = uploaded_master.getvalue()
        if uploaded_master.name.lower().endswith('.csv'):
            df_master = pd.read_csv(io.BytesIO(master_bytes))
        else:
            df_master = pd.read_excel(io.BytesIO(master_bytes))
        # store for later
        st.session_state.sim_master_bytes = master_bytes
        st.session_state.sim_master_name = uploaded_master.name
    except Exception as e:
        st.error(f"❌ Gagal load File 1: {e}")
        st.stop()

    # Validate
    missing = [c for c in REQUIRED_MASTER_COLS if c not in df_master.columns]
    if missing:
        st.error(f"❌ File 1 missing kolom: {missing}")
        st.stop()

    n_total = len(df_master)
    n_with_comp = int(df_master['avg_comp_price'].notna().sum())

    vcol1, vcol2, vcol3, vcol4 = st.columns(4)
    with vcol1:
        st.metric("Total SKU", f"{n_total:,}")
    with vcol2:
        st.metric("SKU with comp price", f"{n_with_comp:,}",
                  f"{n_with_comp/n_total*100:.1f}% of total")
    with vcol3:
        bl_counts = df_master['pricing_bl_25'].value_counts().to_dict()
        st.metric("BL distribution", " · ".join([f"{k}: {v}" for k,v in list(bl_counts.items())[:3]]))
    with vcol4:
        st.metric("File", uploaded_master.name)

    with st.expander("👀 Preview top 5 rows", expanded=False):
        st.dataframe(df_master.head(5), use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# ZONE 1B — SCENARIO SOURCE
# ─────────────────────────────────────────────────────────────────────────────
if df_master is not None:
    st.markdown('<div class="section-header">2️⃣ Build Scenario (File 2 atau Manual Builder)</div>',
                unsafe_allow_html=True)

    st.caption(
        "Upload File 2 sebagai titik awal (opsional), atau langsung cari & tambah SKU manual. "
        "Semua harga — baseline & variant — tetap bisa lo edit di tabel. "
        "Begitu lo ubah angka, hasil di bawah otomatis ke-update."
    )

    # Helper: ensure product_id as clean string for fast lookup
    df_master = df_master.copy()
    df_master['product_id'] = df_master['product_id'].astype(str).str.strip()

    # ── OPTIONAL: Upload File 2 to seed the editor ──
    with st.expander("📂 (Opsional) Upload File 2 untuk isi awal", expanded=False):
        uploaded_scenario = st.file_uploader(
            "File 2 — Scenario (product_id, baseline, var_1, var_2, ...)",
            type=['xlsx', 'xls', 'csv'],
            help="Kolom: product_id (wajib), baseline (wajib), var_1, var_2, ... (opsional). "
                 "Setelah di-load, semua nilai tetap bisa lo edit di tabel bawah.",
            key='sim_scenario_upload'
        )
        if uploaded_scenario is not None and uploaded_scenario.name != st.session_state.get('sim_loaded_file2_name'):
            try:
                scenario_bytes = uploaded_scenario.getvalue()
                if uploaded_scenario.name.lower().endswith('.csv'):
                    df_f2 = pd.read_csv(io.BytesIO(scenario_bytes))
                else:
                    df_f2 = pd.read_excel(io.BytesIO(scenario_bytes))

                n_cols = len(df_f2.columns)
                if n_cols < 2:
                    st.error("❌ File 2 minimal 2 kolom (product_id + baseline)")
                else:
                    new_cols = ['product_id', 'baseline'] + [f'var_{i}' for i in range(1, n_cols - 1)]
                    df_f2.columns = new_cols
                    df_f2['product_id'] = df_f2['product_id'].astype(str).str.strip()

                    f2_var_cols = [c for c in df_f2.columns if c.startswith('var_')]
                    # Bump variant count to fit File 2
                    if f2_var_cols:
                        max_var = max(int(c.split('_')[1]) for c in f2_var_cols)
                        st.session_state.sim_manual_variant_count = max(
                            st.session_state.sim_manual_variant_count, max_var)

                    # Merge File 2 rows into the editable scenario state
                    master_pids = set(df_master['product_id'].values)
                    seeded = 0
                    for _, r in df_f2.iterrows():
                        pid = str(r['product_id'])
                        if pid not in master_pids:
                            continue  # skip SKU yang nggak ada di master
                        entry = {'baseline': r['baseline']}
                        for vc in f2_var_cols:
                            if pd.notna(r[vc]):
                                entry[vc] = r[vc]
                        st.session_state.sim_manual_scenarios[pid] = entry
                        seeded += 1

                    st.session_state.sim_loaded_file2_name = uploaded_scenario.name
                    st.success(f"✅ {seeded} SKU dari File 2 dimuat ke editor. Lo bisa edit / tambah SKU di bawah.")
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Gagal load File 2: {e}")

    # ── SEARCH & ADD SKU (autocomplete via multiselect) ──
    st.markdown("##### 🔍 Cari & Tambah SKU")

    # Build option labels for ALL master SKU (multiselect has built-in type-to-filter)
    opt_label_to_pid = {
        f"{row['product_id']} — {str(row['product_name'])[:60]} (Rp {row['selling_price']:,.0f})": row['product_id']
        for _, row in df_master.iterrows()
    }
    pid_to_label = {v: k for k, v in opt_label_to_pid.items()}

    # Pre-select labels for SKU already in scenario state (incl. those from File 2)
    existing_pids = [p for p in st.session_state.sim_manual_scenarios.keys()
                     if p in pid_to_label]
    default_labels = [pid_to_label[p] for p in existing_pids]

    selected_labels = st.multiselect(
        "Ketik product_id atau nama produk — opsi cocok muncul otomatis, lalu pilih:",
        options=list(opt_label_to_pid.keys()),
        default=default_labels,
        key='sim_multiselect',
        help="Ketik sebagian ID / nama → opsi yang cocok langsung muncul. Bisa pilih banyak SKU."
    )
    selected_pids = [str(opt_label_to_pid[lbl]) for lbl in selected_labels]

    # Drop deselected SKU from scenario state
    for pid in list(st.session_state.sim_manual_scenarios.keys()):
        if pid not in selected_pids:
            del st.session_state.sim_manual_scenarios[pid]

    # ── VARIANT COUNT ──
    n_variants = st.number_input(
        "Jumlah variant (selain baseline):",
        min_value=1, max_value=20, value=st.session_state.sim_manual_variant_count, step=1,
        key='sim_n_variants'
    )
    st.session_state.sim_manual_variant_count = n_variants

    df_scenario = None

    if selected_pids:
        # ── QUICK ACTION: apply % to all ──
        st.markdown("##### ⚡ Quick Action — Apply % ke semua SKU terpilih")
        qa_col1, qa_col2, qa_col3 = st.columns([1.5, 1, 1])
        with qa_col1:
            qa_pct = st.slider("Δ% dari baseline:", min_value=-50.0, max_value=50.0,
                               value=0.0, step=0.5, format="%.1f%%", key='sim_qa_pct')
        with qa_col2:
            qa_target = st.selectbox("Apply ke:", [f"Var {i+1}" for i in range(n_variants)],
                                     key='sim_qa_target')
        with qa_col3:
            st.write(""); st.write("")
            if st.button("Apply", key='sim_qa_apply', use_container_width=True):
                target_idx = int(qa_target.split(' ')[1]) - 1
                for pid in selected_pids:
                    base = st.session_state.sim_manual_scenarios.get(pid, {}).get(
                        'baseline',
                        df_master.loc[df_master['product_id'] == pid, 'selling_price'].iloc[0])
                    st.session_state.sim_manual_scenarios.setdefault(pid, {})[f'var_{target_idx+1}'] = \
                        base * (1 + qa_pct / 100)
                st.rerun()

        # ── EDITOR ──
        st.markdown("##### 🧮 Edit harga per SKU")
        st.caption("Baseline default = current selling_price. Edit baseline atau variant mana pun "
                   "— hasil di bawah otomatis ikut berubah.")

        editor_rows = []
        for pid in selected_pids:
            master_row = df_master[df_master['product_id'] == pid].iloc[0]
            current_price = master_row['selling_price']
            scn = st.session_state.sim_manual_scenarios.get(pid, {})
            row = {
                'product_id': pid,
                'product_name': str(master_row['product_name'])[:50],
                'current_price': current_price,
                'baseline': scn.get('baseline', current_price),
            }
            for i in range(n_variants):
                vk = f'var_{i+1}'
                row[vk] = scn.get(vk, scn.get('baseline', current_price))
            editor_rows.append(row)

        editor_df = pd.DataFrame(editor_rows)

        edited_df = st.data_editor(
            editor_df,
            column_config={
                'product_id':    st.column_config.TextColumn("Product ID", disabled=True, width="small"),
                'product_name':  st.column_config.TextColumn("Product Name", disabled=True, width="medium"),
                'current_price': st.column_config.NumberColumn("Current Price", disabled=True, format="%.0f", width="small"),
                'baseline':      st.column_config.NumberColumn("Baseline", format="%.0f", width="small"),
                **{f'var_{i+1}': st.column_config.NumberColumn(f"Var {i+1}", format="%.0f", width="small")
                   for i in range(n_variants)}
            },
            hide_index=True,
            use_container_width=True,
            key='sim_editor'
        )

        # Persist edited values back to state
        for _, row in edited_df.iterrows():
            pid = str(row['product_id'])
            st.session_state.sim_manual_scenarios[pid] = {
                'baseline': row['baseline'],
                **{f'var_{i+1}': row[f'var_{i+1}'] for i in range(n_variants)}
            }

        # Build df_scenario
        df_scenario = pd.DataFrame([
            {
                'product_id': pid,
                'baseline': st.session_state.sim_manual_scenarios[pid].get('baseline'),
                **{f'var_{i+1}': st.session_state.sim_manual_scenarios[pid].get(f'var_{i+1}')
                   for i in range(n_variants)}
            }
            for pid in selected_pids
        ])

    # ── AUTO-RECOMPUTE (no Run button) ──
    if df_scenario is not None and not df_scenario.empty:
        try:
            result = sim_compute(df_master, df_scenario)
            st.session_state.sim_result = result
            # Full-universe impact (all of File 1; only changed SKU move)
            st.session_state.sim_overall = compute_overall_impact(df_master, df_scenario)
            # Stash scenario bytes so Excel builder can reuse it
            buf = io.BytesIO()
            df_scenario.to_csv(buf, index=False)
            st.session_state.sim_scenario_bytes = buf.getvalue()
            st.session_state.sim_scenario_name = "_manual_scenario.csv"
            st.session_state.sim_excel_ready = False
            if 'sim_excel_bytes' in st.session_state:
                del st.session_state.sim_excel_bytes
            st.caption(f"🔄 Auto-updated · {result['meta']['n_sku_simulated']:,} SKU · "
                       f"{result['meta']['n_variants']} variants")
        except Exception as e:
            st.error(f"❌ Simulation error: {e}")
            import traceback
            st.code(traceback.format_exc())
    else:
        st.session_state.sim_result = None
        st.session_state.sim_overall = None


# ═══════════════════════════════════════════════════════════════════════════
# DASHBOARD — only if result available
# ═══════════════════════════════════════════════════════════════════════════
if st.session_state.sim_result is not None:
    R = st.session_state.sim_result
    df = R['df_sim']
    summary = R['summary']
    by_bl = R['by_bl']
    by_l1 = R['by_l1']
    pi_dist = R['pi_distribution']
    flags = R['framework_flags']
    scenarios = R['scenarios']
    variant_cols = R['variant_cols']

    # ─────────────────────────────────────────────────────────────────────────
    # ZONE 2 — EXECUTIVE SUMMARY
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">3️⃣ Executive Summary</div>', unsafe_allow_html=True)

    O = st.session_state.get('sim_overall')
    baseline_row = summary[summary['scenario'] == 'baseline'].iloc[0]

    # ── Helper: pair table (Baseline vs ONE variant) with Diff & Diff% ──
    def pair_table(rows, label_col, label_title, v, value_kind='money'):
        """
        rows: list of dicts, each must have label_col, 'gv_baseline','gp_baseline',
              'gp_pct_baseline', and the same for variant v.
        Builds a tidy df: <label> | Baseline | <v> | Diff | Diff% per metric block.
        Returns a styled df for GV, GP, GP%.
        """
        out = []
        for r in rows:
            base_gv, var_gv = r['gv_baseline'], r[f'gv_{v}']
            base_gp, var_gp = r['gp_baseline'], r[f'gp_{v}']
            base_pct = r['gp_pct_baseline']; var_pct = r[f'gp_pct_{v}']
            out.append({
                label_title: r[label_col],
                'GV Baseline': base_gv, f'GV {v}': var_gv,
                'GV Diff': var_gv - base_gv,
                'GV Diff%': (var_gv - base_gv) / base_gv if base_gv else np.nan,
                'GP Baseline': base_gp, f'GP {v}': var_gp,
                'GP Diff': var_gp - base_gp,
                'GP Diff%': (var_gp - base_gp) / base_gp if base_gp else np.nan,
                'GP% Baseline': base_pct, f'GP% {v}': var_pct,
                'GP% Diff (pp)': var_pct - base_pct,
            })
        df_pair = pd.DataFrame(out)
        fmt = {
            'GV Baseline': '{:,.0f}', f'GV {v}': '{:,.0f}', 'GV Diff': '{:+,.0f}', 'GV Diff%': '{:+.1%}',
            'GP Baseline': '{:,.0f}', f'GP {v}': '{:,.0f}', 'GP Diff': '{:+,.0f}', 'GP Diff%': '{:+.1%}',
            'GP% Baseline': '{:.1%}', f'GP% {v}': '{:.1%}', 'GP% Diff (pp)': '{:+.2%}',
        }

        def _color(val):
            if isinstance(val, (int, float)) and not pd.isna(val):
                if val > 0: return 'color: #16a34a'
                if val < 0: return 'color: #dc2626'
            return ''
        diff_cols = ['GV Diff', 'GV Diff%', 'GP Diff', 'GP Diff%', 'GP% Diff (pp)']
        sty = df_pair.style.format(fmt, na_rep='—').map(_color, subset=diff_cols)
        return sty

    if O is None or O['overall'].empty:
        st.info("Edit minimal 1 SKU untuk melihat Executive Summary.")
    else:
        ov = O['overall'].set_index('scenario')
        ov_base = ov.loc['baseline']
        n_total   = int(ov_base['n_sku_total'])
        n_changed = int(ov_base['n_sku_changed'])

        # ── BUILD DYNAMIC LENS OPTIONS ──
        by_bl_o = O['by_bl']
        by_l1_o = O['by_l1']
        bl_touched = by_bl_o[by_bl_o['n_sku_changed'] > 0] if not by_bl_o.empty else pd.DataFrame()
        l1_touched = by_l1_o[by_l1_o['n_sku_changed'] > 0] if not by_l1_o.empty else pd.DataFrame()

        lens_options = ["🏢 Overall Astro"]
        if not l1_touched.empty:
            lens_options.append(f"🗂️ L1 Category ({len(l1_touched)} terdampak)")
        if not bl_touched.empty:
            lens_options.append(f"🧱 Pricing BL ({len(bl_touched)} terdampak)")
        lens_options.append(f"🎯 SKU Diubah ({n_changed})")

        st.markdown("##### 🔭 Pilih Lensa")
        lens = st.radio("Lihat dampak dari sudut pandang:", lens_options,
                        horizontal=True, key='sim_lens', label_visibility="collapsed")

        st.markdown("")

        # ═══════════════════ LENS: OVERALL (cards + pair tables) ═══════════════
        if lens.startswith("🏢"):
            st.caption(f"Basis: seluruh {n_total:,} SKU di File 1 (semua penjualan dalam range). "
                       f"Hanya {n_changed:,} SKU yang harganya diubah — sisanya tetap harga asli.")
            ob1, ob2, ob3, ob4 = st.columns(4)
            with ob1:
                st.markdown(kpi_card("Overall GV (baseline)", fmt_money(ov_base['gv'])), unsafe_allow_html=True)
            with ob2:
                st.markdown(kpi_card("Overall GP (baseline)", fmt_money(ov_base['gp'])), unsafe_allow_html=True)
            with ob3:
                st.markdown(kpi_card("Overall GP% (baseline)", fmt_pct(ov_base['gp_pct'])), unsafe_allow_html=True)
            with ob4:
                st.markdown(kpi_card("SKU diubah", f"{n_changed:,}",
                                      sub=f"dari {n_total:,} total SKU"), unsafe_allow_html=True)

            for v in variant_cols:
                ov_v = ov.loc[v]
                d_gv, d_gp = ov_v['gv'] - ov_base['gv'], ov_v['gp'] - ov_base['gp']
                d_gp_pct = ov_v['gp_pct'] - ov_base['gp_pct']
                share_gp = d_gp / ov_base['gp'] if ov_base['gp'] else np.nan
                st.markdown(f"**↓ Impact `{v}` ke Overall Astro**")
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.markdown(kpi_card(f"Overall GV — {v}", fmt_money(ov_v['gv']),
                                          delta=d_gv, delta_label=fmt_money_delta(d_gv)), unsafe_allow_html=True)
                with c2:
                    st.markdown(kpi_card(f"Overall GP — {v}", fmt_money(ov_v['gp']),
                                          delta=d_gp, delta_label=fmt_money_delta(d_gp)), unsafe_allow_html=True)
                with c3:
                    st.markdown(kpi_card(f"Overall GP% — {v}", fmt_pct(ov_v['gp_pct']),
                                          delta=d_gp_pct, delta_label=fmt_pct_delta(d_gp_pct)), unsafe_allow_html=True)
                with c4:
                    st.markdown(kpi_card(f"Δ GP share — {v}",
                                          fmt_pct(share_gp) if pd.notna(share_gp) else "—",
                                          sub="Δ GP ÷ GP Astro baseline"), unsafe_allow_html=True)

        # ═══════════════════ LENS: L1 CATEGORY (pair tables) ══════════════════
        elif lens.startswith("🗂️"):
            st.caption("Hanya L1 yang punya minimal 1 SKU diubah. Angka = agregat seluruh SKU di L1 itu. "
                       "Satu tabel per variant: Baseline vs variant, beserta Diff & Diff%.")
            t = l1_touched.copy()
            if variant_cols and f'd_gp_{variant_cols[0]}' in t.columns:
                t = t.reindex(t[f'd_gp_{variant_cols[0]}'].abs().sort_values(ascending=False).index)
            rows = t.to_dict('records')
            for v in variant_cols:
                st.markdown(f"**📊 Baseline vs `{v}` — per L1 Category**")
                st.dataframe(pair_table(rows, 'l1_category_name', 'L1 Category', v),
                             use_container_width=True, hide_index=True)

        # ═══════════════════ LENS: PRICING BL (pair tables) ═══════════════════
        elif lens.startswith("🧱"):
            st.caption("Hanya Pricing BL yang punya minimal 1 SKU diubah. Angka = agregat seluruh SKU di BL itu. "
                       "Satu tabel per variant: Baseline vs variant, beserta Diff & Diff%.")
            t = bl_touched.copy()
            if variant_cols and f'd_gp_{variant_cols[0]}' in t.columns:
                t = t.reindex(t[f'd_gp_{variant_cols[0]}'].abs().sort_values(ascending=False).index)
            rows = t.to_dict('records')
            for v in variant_cols:
                st.markdown(f"**📊 Baseline vs `{v}` — per Pricing BL**")
                st.dataframe(pair_table(rows, 'pricing_bl_25', 'Pricing BL', v),
                             use_container_width=True, hide_index=True)

        # ═══════════════════ LENS: SKU DIUBAH (cards + pair tables w/ PI) ═════
        else:
            st.caption("Fokus ke SKU yang lo reprice. PI = PI Blended Avg "
                       "(selling_price × 100 ÷ avg_comp_price), qty-weighted — sengaja hanya SKU diubah, "
                       "karena PI itu metrik posisi harga per-SKU vs kompetitor.")
            bcol1, bcol2, bcol3, bcol4 = st.columns(4)
            with bcol1:
                st.markdown(kpi_card("Baseline GV", fmt_money(baseline_row['gv'])), unsafe_allow_html=True)
            with bcol2:
                st.markdown(kpi_card("Baseline GP", fmt_money(baseline_row['gp'])), unsafe_allow_html=True)
            with bcol3:
                st.markdown(kpi_card("Baseline GP%", fmt_pct(baseline_row['gp_pct'])), unsafe_allow_html=True)
            with bcol4:
                st.markdown(kpi_card("Baseline Avg PI", fmt_pi_detail(baseline_row['pi_avg_w']),
                                      sub=f"Last day PI: {fmt_pi_detail(baseline_row['pi_last_w'])}"),
                            unsafe_allow_html=True)

            for v in variant_cols:
                v_row = summary[summary['scenario'] == v].iloc[0]
                d_gv = v_row['gv'] - baseline_row['gv']
                d_gp = v_row['gp'] - baseline_row['gp']
                d_gp_pct = v_row['gp_pct'] - baseline_row['gp_pct']
                d_pi_avg = v_row['pi_avg_w'] - baseline_row['pi_avg_w']
                d_pi_last = v_row['pi_last_w'] - baseline_row['pi_last_w']
                st.markdown(f"**↓ Impact `{v}` (SKU diubah)**")
                vc1, vc2, vc3, vc4 = st.columns(4)
                with vc1:
                    st.markdown(kpi_card(f"GV — {v}", fmt_money(v_row['gv']),
                                          delta=d_gv, delta_label=fmt_money_delta(d_gv)), unsafe_allow_html=True)
                with vc2:
                    st.markdown(kpi_card(f"GP — {v}", fmt_money(v_row['gp']),
                                          delta=d_gp, delta_label=fmt_money_delta(d_gp)), unsafe_allow_html=True)
                with vc3:
                    st.markdown(kpi_card(f"GP% — {v}", fmt_pct(v_row['gp_pct']),
                                          delta=d_gp_pct, delta_label=fmt_pct_delta(d_gp_pct)), unsafe_allow_html=True)
                with vc4:
                    st.markdown(kpi_card(f"PI Avg — {v}", fmt_pi_detail(v_row['pi_avg_w']),
                                          delta=d_pi_avg, delta_label=fmt_pi_delta(d_pi_avg),
                                          sub=f"Δ PI Last: {fmt_pi_delta(d_pi_last)}",
                                          delta_inverse=True), unsafe_allow_html=True)

        st.markdown("---")


    # ─────────────────────────────────────────────────────────────────────────
    # ZONE 3 — PER-SKU DETAIL TABLE
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">4️⃣ Per-SKU Detail</div>', unsafe_allow_html=True)
    st.caption("Detail per SKU dengan harga, GP, margin, dan 3 versi PI per scenario. Klik header kolom untuk sort.")

    # Build display table — limit columns to readable subset
    info_cols = ['product_id', 'product_name', 'l1_category_name', 'pricing_bl_25',
                 'qty', 'cost_price', 'avg_comp_price', 'last_comp_price', 'last_price']
    price_cols = scenarios  # baseline + var_1, var_2, ...
    gp_pct_cols = [f'gp_pct_{s}' for s in scenarios]
    pi_avg_cols = [f'pi_avg_{s}' for s in scenarios]
    pi_last_cols = [f'pi_last_{s}' for s in scenarios]
    delta_gp_cols = [f'd_gp_{v}' for v in variant_cols]
    delta_pi_cols = [f'd_pi_avg_{v}' for v in variant_cols]

    display_cols = info_cols + price_cols + gp_pct_cols + pi_avg_cols + pi_last_cols + \
                   ['pi_last_with_lp'] + delta_gp_cols + delta_pi_cols

    display_cols = [c for c in display_cols if c in df.columns]

    # View toggle
    detail_view = st.radio("View:", ["Compact (key cols only)", "Wide (all scenarios)"],
                           horizontal=True, key='sim_detail_view')

    if detail_view == "Compact (key cols only)":
        # Show only: info + baseline price + each variant price + d_gp + d_pi_avg
        compact_cols = ['product_id', 'product_name', 'pricing_bl_25',
                       'qty', 'cost_price', 'avg_comp_price',
                       'baseline', 'gp_baseline', 'gp_pct_baseline',
                       'pi_avg_baseline', 'pi_last_baseline', 'pi_last_with_lp']
        for v in variant_cols:
            compact_cols += [v, f'gp_{v}', f'pi_avg_{v}', f'd_gp_{v}', f'd_pi_avg_{v}']
        show = df[[c for c in compact_cols if c in df.columns]].copy()
    else:
        show = df[display_cols].copy()

    # Format display
    fmt_dict = {}
    for c in show.columns:
        if c in ('qty', 'cost_price', 'avg_comp_price', 'last_comp_price', 'last_price'):
            fmt_dict[c] = '{:,.0f}'
        elif c == 'baseline' or c.startswith('var_'):
            fmt_dict[c] = '{:,.0f}'
        elif c.startswith('gv_') or c.startswith('gp_') and not c.startswith('gp_pct'):
            fmt_dict[c] = '{:,.0f}'
        elif c.startswith('gp_pct'):
            fmt_dict[c] = '{:.1%}'
        elif c.startswith('pi_avg') or c.startswith('pi_last') or c == 'pi_last_with_lp':
            fmt_dict[c] = '{:.3f}'
        elif c.startswith('d_gp_pct') or c.startswith('d_gp_pp'):
            fmt_dict[c] = '{:+.2%}'
        elif c.startswith('d_pi'):
            fmt_dict[c] = '{:+.3f}'
        elif c.startswith('d_'):
            fmt_dict[c] = '{:+,.0f}'

    st.dataframe(
        show.style.format(fmt_dict, na_rep='—'),
        use_container_width=True, hide_index=True, height=500
    )


    # ─────────────────────────────────────────────────────────────────────────
    # ZONE 4 — BY DIMENSION
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">5️⃣ Aggregated by Dimension</div>', unsafe_allow_html=True)

    dim_tabs = st.tabs(["By Business Line", "By L1 Category", "By L2 Category"])

    with dim_tabs[0]:
        if not by_bl.empty:
            cols_show = ['pricing_bl_25', 'n_sku']
            for s in scenarios:
                cols_show += [f'gv_{s}', f'gp_{s}', f'gp_pct_{s}', f'pi_avg_{s}']
            for v in variant_cols:
                cols_show += [f'd_gp_{v}', f'd_pi_avg_{v}']
            cols_show = [c for c in cols_show if c in by_bl.columns]

            fmt = {}
            for c in cols_show:
                if 'gp_pct' in c:
                    fmt[c] = '{:.1%}'
                elif 'pi_' in c and 'd_' not in c:
                    fmt[c] = '{:.3f}'
                elif 'd_pi' in c:
                    fmt[c] = '{:+.3f}'
                elif 'd_' in c:
                    fmt[c] = '{:+,.0f}'
                elif c == 'n_sku':
                    fmt[c] = '{:,}'
                elif c.startswith('gv_') or c.startswith('gp_'):
                    fmt[c] = '{:,.0f}'

            st.dataframe(by_bl[cols_show].style.format(fmt, na_rep='—'),
                         use_container_width=True, hide_index=True)
        else:
            st.info("Tidak ada data per BL")

    with dim_tabs[1]:
        if not by_l1.empty:
            cols_show = ['l1_category_name', 'n_sku']
            for s in scenarios:
                cols_show += [f'gv_{s}', f'gp_{s}', f'gp_pct_{s}', f'pi_avg_{s}']
            for v in variant_cols:
                cols_show += [f'd_gp_{v}', f'd_pi_avg_{v}']
            cols_show = [c for c in cols_show if c in by_l1.columns]

            fmt = {}
            for c in cols_show:
                if 'gp_pct' in c: fmt[c] = '{:.1%}'
                elif 'pi_' in c and 'd_' not in c: fmt[c] = '{:.3f}'
                elif 'd_pi' in c: fmt[c] = '{:+.3f}'
                elif 'd_' in c: fmt[c] = '{:+,.0f}'
                elif c == 'n_sku': fmt[c] = '{:,}'
                elif c.startswith('gv_') or c.startswith('gp_'): fmt[c] = '{:,.0f}'

            st.dataframe(by_l1[cols_show].style.format(fmt, na_rep='—'),
                         use_container_width=True, hide_index=True, height=400)
        else:
            st.info("Tidak ada data per L1")

    with dim_tabs[2]:
        by_l2 = R.get('by_l2', pd.DataFrame())
        if not by_l2.empty:
            cols_show = ['l2_category_name', 'n_sku']
            for s in scenarios:
                cols_show += [f'gv_{s}', f'gp_{s}', f'gp_pct_{s}', f'pi_avg_{s}']
            for v in variant_cols:
                cols_show += [f'd_gp_{v}', f'd_pi_avg_{v}']
            cols_show = [c for c in cols_show if c in by_l2.columns]

            fmt = {}
            for c in cols_show:
                if 'gp_pct' in c: fmt[c] = '{:.1%}'
                elif 'pi_' in c and 'd_' not in c: fmt[c] = '{:.3f}'
                elif 'd_pi' in c: fmt[c] = '{:+.3f}'
                elif 'd_' in c: fmt[c] = '{:+,.0f}'
                elif c == 'n_sku': fmt[c] = '{:,}'
                elif c.startswith('gv_') or c.startswith('gp_'): fmt[c] = '{:,.0f}'

            st.dataframe(by_l2[cols_show].style.format(fmt, na_rep='—'),
                         use_container_width=True, hide_index=True, height=400)
        else:
            st.info("Tidak ada data per L2")


    # ─────────────────────────────────────────────────────────────────────────
    # ZONE 5 — SCENARIO COMPARISON CHARTS
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">6️⃣ Scenario Comparison Charts</div>', unsafe_allow_html=True)

    chart_tab = st.tabs(["GP per Scenario", "Top Movers (Δ GP)", "PI vs Margin"])

    with chart_tab[0]:
        # Bar chart
        fig = go.Figure()
        for _, row in summary.iterrows():
            color = '#2563EB' if row['scenario'] == 'baseline' else '#10B981'
            fig.add_trace(go.Bar(
                x=[row['scenario']], y=[row['gp']],
                name=row['scenario'], marker_color=color,
                text=[fmt_money(row['gp'])], textposition='outside',
            ))
        fig.update_layout(
            title="Total GP per Scenario",
            xaxis_title="Scenario",
            yaxis_title="GP (Rupiah)",
            height=400, showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)

    with chart_tab[1]:
        # Pick variant
        if variant_cols:
            v_pick = st.selectbox("Pilih variant:", variant_cols, key='sim_chart_var')
            top_gainers = df.nlargest(15, f'd_gp_{v_pick}')[['product_name', f'd_gp_{v_pick}']]
            top_losers  = df.nsmallest(15, f'd_gp_{v_pick}')[['product_name', f'd_gp_{v_pick}']]

            tg, tl = st.columns(2)
            with tg:
                st.markdown(f"**🔼 Top 15 GP Gainers (Δ vs Baseline) — {v_pick}**")
                fig_g = go.Figure(go.Bar(
                    y=top_gainers['product_name'].str[:40][::-1],
                    x=top_gainers[f'd_gp_{v_pick}'][::-1],
                    orientation='h', marker_color='#10B981',
                    text=top_gainers[f'd_gp_{v_pick}'][::-1].apply(fmt_money_delta),
                    textposition='outside',
                ))
                fig_g.update_layout(height=500, margin=dict(l=200), xaxis_title="Δ GP (Rp)")
                st.plotly_chart(fig_g, use_container_width=True)
            with tl:
                st.markdown(f"**🔽 Top 15 GP Losers (Δ vs Baseline) — {v_pick}**")
                fig_l = go.Figure(go.Bar(
                    y=top_losers['product_name'].str[:40][::-1],
                    x=top_losers[f'd_gp_{v_pick}'][::-1],
                    orientation='h', marker_color='#DC2626',
                    text=top_losers[f'd_gp_{v_pick}'][::-1].apply(fmt_money_delta),
                    textposition='outside',
                ))
                fig_l.update_layout(height=500, margin=dict(l=200), xaxis_title="Δ GP (Rp)")
                st.plotly_chart(fig_l, use_container_width=True)

    with chart_tab[2]:
        # Scatter PI vs Margin
        scn_pick = st.selectbox("Pilih scenario:", scenarios, key='sim_scatter_scn')
        scatter_df = df[[f'pi_avg_{scn_pick}', f'gp_pct_{scn_pick}', 'product_name', 'pricing_bl_25', 'qty']].copy()
        scatter_df = scatter_df.dropna(subset=[f'pi_avg_{scn_pick}', f'gp_pct_{scn_pick}'])

        fig_sc = px.scatter(
            scatter_df, x=f'pi_avg_{scn_pick}', y=f'gp_pct_{scn_pick}',
            color='pricing_bl_25', size='qty',
            hover_data=['product_name'],
            title=f"PI vs Margin — Scenario {scn_pick}",
            labels={f'pi_avg_{scn_pick}': 'PI Avg Comp', f'gp_pct_{scn_pick}': 'Margin %'}
        )
        fig_sc.add_hline(y=0, line_dash="dash", line_color="grey")
        fig_sc.add_vline(x=100, line_dash="dash", line_color="grey")
        fig_sc.update_layout(height=550)
        st.plotly_chart(fig_sc, use_container_width=True)


    # ─────────────────────────────────────────────────────────────────────────
    # ZONE 6 — PI DISTRIBUTION
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">7️⃣ PI Distribution per Scenario</div>', unsafe_allow_html=True)
    st.caption("Berapa SKU di bucket PI mana per scenario. Pakai PI Avg Comp sebagai basis.")

    # Show distribution table + chart
    dist_show = pi_dist.copy()
    dist_show.index = dist_show['scenario']
    dist_chart_df = dist_show.drop(columns=['scenario', 'total'])

    pi_col1, pi_col2 = st.columns([2, 3])
    with pi_col1:
        st.markdown("**SKU Count per Bucket**")
        st.dataframe(pi_dist, use_container_width=True, hide_index=True)

    with pi_col2:
        # Stacked bar
        fig_pi = go.Figure()
        bucket_colors = {
            'A.<95':      '#10B981',  # green - kompetitif
            'B.95-<100':  '#84CC16',
            'C.100-105':  '#FACC15',
            'D.105-110':  '#FB923C',
            'E.110-120':  '#F87171',
            'F.>120':     '#DC2626',  # red - premium
        }
        for bucket in ['A.<95', 'B.95-<100', 'C.100-105', 'D.105-110', 'E.110-120', 'F.>120']:
            if bucket in dist_chart_df.columns:
                fig_pi.add_trace(go.Bar(
                    name=bucket, x=dist_chart_df.index, y=dist_chart_df[bucket],
                    marker_color=bucket_colors[bucket]
                ))
        fig_pi.update_layout(
            barmode='stack', height=400,
            xaxis_title="Scenario", yaxis_title="# SKU",
            title="PI Bucket Distribution per Scenario"
        )
        st.plotly_chart(fig_pi, use_container_width=True)


    # ─────────────────────────────────────────────────────────────────────────
    # ZONE 7 — FRAMEWORK FLAGS
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">8️⃣ Framework Flags per Scenario</div>', unsafe_allow_html=True)
    st.caption("SKU yang trigger framework rule (butuh repricing action) di setiap scenario. "
              "Lihat Page 5 Glossary untuk detail rule.")

    flags_show = flags.copy()
    flags_show.columns = [c.replace('_', ' ').title() for c in flags_show.columns]
    st.dataframe(flags_show, use_container_width=True, hide_index=True)


    # ─────────────────────────────────────────────────────────────────────────
    # ZONE 8 — DOWNLOAD EXCEL
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">9️⃣ Download Full Report</div>', unsafe_allow_html=True)
    st.caption("Excel 8 sheets: Master Data, SKU Detail (wide pivot), Summary KPI, By BL, By L1, "
              "PI Distribution, Framework Flags, Glossary.")

    if not st.session_state.sim_excel_ready:
        if st.button("🔨 Build Excel Report", type="primary", key='sim_excel_build'):
            with st.spinner("Building Excel..."):
                try:
                    xb = cached_sim_excel(
                        st.session_state.sim_master_bytes,
                        st.session_state.sim_master_name,
                        st.session_state.sim_scenario_bytes,
                        st.session_state.sim_scenario_name,
                    )
                    st.session_state.sim_excel_bytes = xb
                    st.session_state.sim_excel_ready = True
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Excel error: {e}")
                    import traceback
                    st.code(traceback.format_exc())
    else:
        st.success(f"✅ Excel ready ({len(st.session_state.sim_excel_bytes)/1024:.1f} KB)")
        st.download_button(
            "📥 Download Excel Report",
            data=st.session_state.sim_excel_bytes,
            file_name=f"price_simulation_{R['meta']['n_variants']}variants.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )
        if st.button("🔄 Rebuild", type="secondary", key='sim_excel_rebuild'):
            st.session_state.sim_excel_ready = False
            if 'sim_excel_bytes' in st.session_state:
                del st.session_state.sim_excel_bytes
            st.rerun()

else:
    if df_master is None:
        st.info("⬆️ Upload File 1 (Master Data) untuk mulai simulasi.")
