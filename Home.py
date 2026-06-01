"""
Astro Pricing Strategy Toolkit — Landing Page
"""
import streamlit as st

st.set_page_config(
    page_title="Astro Pricing Toolkit",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Header
st.markdown("""
<style>
    .main > div { padding-top: 2rem; }
    .hero-title {
        font-size: 42px; font-weight: 800; color: #111827;
        margin-bottom: 4px;
    }
    .hero-sub {
        font-size: 18px; color: #6B7280; margin-bottom: 32px;
    }
    .tool-card {
        border: 1px solid #E5E7EB;
        border-radius: 12px;
        padding: 24px;
        background: #FFFFFF;
        margin-bottom: 16px;
        height: 100%;
    }
    .tool-title { font-size: 22px; font-weight: 700; color: #111827; margin-bottom: 8px; }
    .tool-sub { font-size: 14px; color: #6B7280; margin-bottom: 16px; }
    .tool-tag { font-size: 11px; color: #2563EB; background: #DBEAFE;
                padding: 4px 10px; border-radius: 12px; display: inline-block;
                font-weight: 600; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="hero-title">🛒 Astro Pricing Strategy Toolkit</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">Internal analysis suite — PVM decomposition & PI movement diagnostics</div>',
            unsafe_allow_html=True)

st.markdown("---")
st.markdown("### Pilih Tool")

c1, c2 = st.columns(2)

with c1:
    st.markdown("""
    <div class="tool-card">
        <span class="tool-tag">PRICING × VOLUME × MIX</span>
        <div class="tool-title" style="margin-top: 8px;">📊 PVM Analyzer</div>
        <div class="tool-sub">
            Decompose GP & Margin changes into Cost, Price, Vol/Mix, Churned, dan New SKU effects.
            Drilldown ke L1 category + Top movers per SKU.
        </div>
        <div style="font-size: 13px; color: #374151;">
            <strong>Use cases:</strong><br>
            • Why margin changed week-over-week<br>
            • Identify best/worst SKUs by GP impact<br>
            • BL contribution + L1 category breakdown<br>
            • Watch list: Priority / Review / Framework
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/1_📊_PVM_Analyzer.py", label="→ Buka PVM Analyzer", icon="📊")

with c2:
    st.markdown("""
    <div class="tool-card">
        <span class="tool-tag">PRICING INDEX</span>
        <div class="tool-title" style="margin-top: 8px;">📈 PI Analyzer</div>
        <div class="tool-sub">
            Diagnose PI movement vs competitor. Shapley decomposition: Price Effect, Comp Effect,
            Churned SKU, New SKU. Quadrant analysis & framework check.
        </div>
        <div style="font-size: 13px; color: #374151;">
            <strong>Use cases:</strong><br>
            • Why PI shifted vs competitor<br>
            • SKU yang perlu repricing (framework check)<br>
            • COGS Index categories yang perlu vendor negotiation<br>
            • PI vs Margin quadrant for strategic decisions
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/2_📈_PI_Analyzer.py", label="→ Buka PI Analyzer", icon="📈")

# Row 2: Price Simulator + Query Builder
c3, c4 = st.columns(2)

with c3:
    st.markdown("""
    <div class="tool-card">
        <span class="tool-tag">WHAT-IF PRICE SCENARIO</span>
        <div class="tool-title" style="margin-top: 8px;">⚖️ Price Simulator</div>
        <div class="tool-sub">
            Simulate dampak perubahan harga ke GP, Margin, dan PI per SKU.
            Upload File 2 atau bikin scenario manual dengan multi-variant.
        </div>
        <div style="font-size: 13px; color: #374151;">
            <strong>Use cases:</strong><br>
            • What-if margin kalau harga turun 5%<br>
            • Compare 2-3 scenarios side-by-side<br>
            • Identify SKU yang aman naik/turun harga<br>
            • Output Excel multi-sheet
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/3_⚖️_Simulator.py", label="→ Buka Simulator", icon="⚖️")

with c4:
    st.markdown("""
    <div class="tool-card">
        <span class="tool-tag">SQL TEMPLATE GENERATOR</span>
        <div class="tool-title" style="margin-top: 8px;">🔍 Query Builder</div>
        <div class="tool-sub">
            Generate parameterized BigQuery SQL untuk PVM, PI, dan Page 3 analysis.
            Tinggal pilih hari + tanggal, query auto-generated dengan substitution otomatis.
        </div>
        <div style="font-size: 13px; color: #374151;">
            <strong>Tools available:</strong><br>
            • Query 1 — PVM (weekly comparison)<br>
            • Query 2 — PI (weekly comparison)<br>
            • Query 3 — Date range analysis
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/4_🔍_Query_Builder.py", label="→ Buka Query Builder", icon="🔍")

# Row 3: Glossary
c5, c6 = st.columns(2)

with c5:
    st.markdown("""
    <div class="tool-card">
        <span class="tool-tag">REFERENCE</span>
        <div class="tool-title" style="margin-top: 8px;">📚 Glossary & Methodology</div>
        <div class="tool-sub">
            Lengkap dokumentasi semua definisi, threshold, dan methodologi yang dipakai di
            PVM Analyzer + PI Analyzer + Simulator.
        </div>
        <div style="font-size: 13px; color: #374151;">
            <strong>Sections:</strong><br>
            • Konsep dasar (PI, PVM, GP, CI)<br>
            • Tagging & Threshold<br>
            • Bucket definition & PI Positioning<br>
            • Methodology (Shapley, Margin Bridge)
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/5_📚_Glossary.py", label="→ Buka Glossary", icon="📚")

st.markdown("---")

with st.expander("ℹ️ Tentang Toolkit Ini"):
    st.markdown("""
    **Built by:** Shadqi (Pricing Strategy Analyst, Astro)

    **Tech stack:** Streamlit + Pandas + Openpyxl + Plotly

    **Data flow:** Upload raw input → process → render insights + downloadable Excel report

    **Persistence:** Data yang sudah di-process di Page 1 atau Page 2 akan tetap stay
    selama session aktif (gak perlu re-upload saat navigate antar page).

    **Source code:** Internal — Astro Pricing Strategy team
    """)
