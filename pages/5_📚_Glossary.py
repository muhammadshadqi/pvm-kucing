"""
Glossary & Methodology — Page 5 (Pricing Toolkit)
Reference documentation for all definitions, methods, and tagging logic used
in Page 1 (PVM Analyzer) and Page 2 (PI Analyzer).
"""
import streamlit as st
from brand import inject_brand, render_brand_header

st.set_page_config(
    page_title="Glossary — Pricing",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="auto",
)

inject_brand()

render_brand_header("Glossary & Methodology", "Definisi, threshold, dan metodologi — Page 1 (PVM) & Page 2 (PI)")

st.markdown("""
Page ini bukan interactive dashboard — ini **referensi lengkap** untuk istilah, metode tagging,
threshold, dan formula yang dipakai di toolkit. Pakai sebagai panduan kalau ada term yang
kurang familiar.
""")

# ─────────────────────────────────────────────────────────────────────────────
# QUICK NAV
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
**📑 Quick Navigation:**
1. [Konsep Dasar](#konsep-dasar)
2. [Tagging & Threshold](#tagging-threshold)
3. [Bucket Definition](#bucket-definition)
4. [Methodology](#methodology)
5. [Business Line (BL) Categorization](#business-line)
6. [Acronyms & Glossary](#acronyms)
""")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 — KONSEP DASAR
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header" id="konsep-dasar">1️⃣ Konsep Dasar</div>', unsafe_allow_html=True)

st.markdown("""
##### PI — Pricing Index
**Definisi:** Rasio harga vs harga competitor (blended). Formula:

`PI = (Selling Price / Blended Competitor Price) × 100`

- **PI = 100** → kita sama mahalnya dengan competitor
- **PI > 100** → kita lebih mahal (Premium)
- **PI < 100** → kita lebih murah (Undercut)

**Contoh:** Kita jual Rp 12,000, comp blended Rp 10,000 → PI = 120 (20% lebih mahal dari comp)

---

##### PVM — Price × Volume × Mix
**Definisi:** Framework untuk decomposisi perubahan **Gross Profit** atau **Margin** week-over-week ke 5 komponen:
1. **Churned SKU Effect** — pengaruh SKU yang ada di P1 tapi hilang di P2
2. **COGS Effect** — pengaruh perubahan harga pokok (HPP)
3. **Price Effect** — pengaruh perubahan selling price
4. **Vol/Mix Effect** — pengaruh perubahan quantity dan komposisi product mix
5. **New SKU Effect** — pengaruh SKU baru yang muncul di P2

Metodologi: **Sequential Hypothetical Margin Bridge** (lihat Section 4).

---

##### GP — Gross Profit (Margin Absolut)
`GP = Goods Value − COGS`

GP **Rupiah**: absolut, dipengaruhi oleh volume.
GP%: relatif, independen volume.

---

##### COGS Index (CI)
Rasio cost vs comp price.

`COGS Index = (COGS / Blended Competitor Price) × 100`

- **CI < 95** → cost lebih murah dari comp price (cost advantage)
- **CI = 100** → cost = comp price
- **CI > 105** → cost lebih mahal dari comp price (structural loss risk)

**Why important:** CI tinggi = cost negotiation bottleneck. Bahkan kalau jual sama dengan comp, margin akan tipis karena cost-nya sudah mahal.

---

##### Pareto Classification
Kategorisasi SKU berdasarkan kontribusi penjualan:

| Class | Kontribusi |
|---|---|
| **A** | Top SKU — kontribusi terbesar (~5% SKU, ~50% revenue) |
| **B** | Mid-tier (~15% SKU, ~30% revenue) |
| **C** | Tail (~30% SKU, ~15% revenue) |
| **D** | Very tail (~50% SKU, ~5% revenue) |

Pareto class dipakai untuk prioritize action — Class A SKU lebih critical untuk dijaga PI dan margin-nya.
""")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 — TAGGING & THRESHOLD
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header" id="tagging-threshold">2️⃣ Tagging & Threshold</div>', unsafe_allow_html=True)

st.markdown("""
##### Direction Tag (Up / Stay / Down)
Dipakai untuk classify pergerakan **Price** (kita), **COGS**, dan **Comp Price** dari P1 ke P2.

| Tag | Kondisi |
|---|---|
| **Up** | Δ absolute ≥ **+5,000 IDR** **OR** Δ percent ≥ **+5%** |
| **Down** | Δ absolute ≤ **−5,000 IDR** **OR** Δ percent ≤ **−5%** |
| **Stay** | Δ tidak masuk Up atau Down (Δ < 5,000 IDR dan abs Δ% < 5%) |

**Source:** `pi_analyzer_v1.py` engine

---

##### SKU Type Classification

| Type | Definisi |
|---|---|
| **Existing** | SKU yang punya data di P1 **dan** P2 (PI, price, qty terisi di kedua periode) |
| **New** | SKU yang muncul **hanya** di P2 (gak ada di P1) |
| **Departing / Churned** | SKU yang ada di P1 tapi **hilang** di P2 |

Effects per SKU type:
- `Existing` → kontribusi ke Price Effect, Comp Effect, COGS Effect, Vol/Mix Effect
- `New` → kontribusi ke New SKU Effect (full magnitude)
- `Departing/Churned` → kontribusi ke Churned SKU Effect (full magnitude)

---

##### Framework Check (5 Rules)
SKU yang memenuhi salah satu kondisi ini di-flag butuh **repricing action**:

| Rule | Kondisi | Action |
|---|---|---|
| 1 | Fresh, PI > 110, Margin ≤ 15% | Room to drop price (uncompetitive + low margin) |
| 2 | Frozen, PI > 100, Margin ≤ 15% | Room to drop (Frozen lebih sensitive ke PI) |
| 3 | Fresh, PI > 120, Margin ≥ 70% | Over-priced premium (terlalu mahal) |
| 4 | Dry, PI < 105, Margin ≤ 0% | Loss leader — raise price |
| 5 | Dry, PI > 120, Margin > 40% | Over-priced — drop price |

Output di Zone 9 Page 2 (PI Analyzer): list SKU yang trigger rule berapa.

---

##### Source Status
Klasifikasi sumber produk:

| Status | Arti |
|---|---|
| **SOURCE** | SKU yang kita sumber langsung (typical 75% dari portfolio) |
| **NON SOURCE** | SKU yang kita gak sumber langsung |

PI analysis di engine pakai filter `source_status = 'SOURCE'` untuk consistency.
""")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 — BUCKET DEFINITION
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header" id="bucket-definition">3️⃣ Bucket Definition</div>', unsafe_allow_html=True)

st.markdown("""
##### PI Bucket
| Bucket | Range PI | Interpretation |
|---|---|---|
| **A** | < 95 | Sangat kompetitif (>5% lebih murah) |
| **B** | 95 — < 100 | Slightly cheaper |
| **C** | 100 — 105 | Match (±5% dari comp) |
| **D** | 105 — 110 | Slightly premium |
| **E** | 110 — 120 | Premium |
| **F** | > 120 | Sangat premium (>20% lebih mahal) |

---

##### COGS Index Bucket
| Bucket | Range CI | Interpretation |
|---|---|---|
| **A** | < 70 | Cost super advantage |
| **B** | 70 — 85 | Cost advantage |
| **C** | 85 — 95 | Cost slightly cheaper than comp |
| **D** | 95 — 105 | Cost in line — need attention |
| **E** | > 105 | Cost more expensive than comp — structural risk |

**Note:** CI Group D + E = candidates untuk **vendor negotiation** (Zone 10 Page 2).

---

##### Margin Bucket (Margin %)
| Bucket | Range Margin% |
|---|---|
| **A** | < −20% |
| **B** | −20% to −10% |
| **C** | −10% to 0% |
| **D** | 0% to 10% |
| **E** | 10% to 20% |
| **F** | 20% to 30% |
| **G** | 30% to 50% |
| **H** | > 50% |

---

##### PI Positioning (Aggregated, Page 2 Zone 2)
Aggregation dari PI Bucket untuk executive summary:

| Positioning | PI Range | Buckets included |
|---|---|---|
| 🔴 **Premium** | PI > 105 | D + E + F |
| 🟡 **Match** | 95 ≤ PI ≤ 105 | B + C |
| 🟢 **Undercut** | PI < 95 | A |

3 kategori ini **exhaustive & mutually exclusive** (sum = 100%).
""")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4 — METHODOLOGY
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header" id="methodology">4️⃣ Methodology</div>', unsafe_allow_html=True)

st.markdown("""
##### A. Shapley PI Decomposition (Page 2)

PI movement dari Avg PI P1 (`A`) ke Avg PI P2 (`E`) di-decompose ke **5 effect** dengan **Shapley value method**:

```
A (baseline P1)
+ 1. Churned SKU Effect
+ 2. Price Change Effect
+ 3. Comp Price Effect
    = 3.1 Normal Comp Effect + 3.2 Discount (Blended) Comp Effect
+ 4. New SKU Effect
= E (result P2)
```

**Math identity:** Total Δ = Sum of all 5 effects (residual = 0, **exact**).

**Why Shapley:** Shapley value menjamin **order-independent** allocation — gak peduli urutan kita
hitung Price vs Comp vs Churned, total effect-nya sama.

**Granularity:**
- `eff_dep` (Churned) — pengaruh SKU yang ada di P1 tapi hilang di P2
- `eff_price` — pengaruh perubahan price
- `eff_normal_comp` — pengaruh perubahan **normal price** competitor (without promo)
- `eff_discount_comp` — pengaruh perubahan **blended price** competitor minus normal effect (= efek dari promo)
- `eff_new` — pengaruh SKU baru di P2

---

##### B. Sequential Hypothetical Margin Bridge (Page 1)

Untuk decompose **change in Gross Profit / Margin**, engine pakai **Sequential Hypothetical Margin Bridge**.

Method ini compute **5 hypothetical scenarios** secara bertahap, di mana masing-masing scenario
hanya ubah 1 variabel sambil hold variabel lain konstan.

```
GP P1 (start)
+ Churned SKU Effect    (apa kalau SKU yang departing di-remove dulu)
+ Existing SKU Effect
    = COGS Effect       (apa kalau COGS Existing SKU pakai P2 cost, sisanya P1)
    + Price Effect      (apa kalau Price Existing SKU pakai P2 price, COGS sudah P2, sisanya P1)
    + Vol/Mix Effect    (apa kalau Qty Existing SKU pakai P2 qty, Price & COGS sudah P2)
+ New SKU Effect        (full GP dari SKU baru di P2)
= GP P2 (end)
```

**Math identity:** GP P2 − GP P1 = Sum of 5 effects (exact).

---

##### C. Exact Contributions Formula

Untuk **per-segment contribution** ke Overall effect (Tabel 2 Page 2 + Tabel 2 Page 1):

```
Contribution of segment S to overall Effect X
= Effect X computed within segment S, weighted by:
   - segment SKU count in P1 (w_ex) for Existing & Comp/Price effects
   - segment SKU count in P2 (w_cur) for Churned effects
   - segment new SKU count (w_nxt) for New SKU effects
```

**Why exact:** Σ Dry + Fresh + Frozen = Overall (zero residual, math identity).

---

##### D. Driver Effect Identification (Page 2 Zone 4 L1)

Untuk identify "driver" per L1 category:

1. Compute 5 leaf effects per L1 (`eff_dep`, `eff_price`, `eff_normal_comp`, `eff_discount_comp`, `eff_new`).
2. Filter ke effects yang punya **sign sama dengan Total Δ** (positif kalau Total Δ positif).
3. Driver = effect dengan **magnitude terbesar** dari filtered set.

**Interpretation:**
- L1 dengan Total Δ positif → driver = effect yang **push PI naik**
- L1 dengan Total Δ negatif → driver = effect yang **push PI turun**

---

##### E. PI Distribution & Movement (Page 2 Zone 6 & 8)

**Zone 6:** SKU count distribution per PI bucket di P1 vs P2 (side-by-side bar chart).

**Zone 8 Tab 4 Transition Matrix:** Rows = PI bucket P1, Cols = PI bucket P2.
- **Diagonal** = SKU stay di bucket sama
- **Upper triangle** = SKU pindah ke bucket lebih tinggi (PI naik)
- **Lower triangle** = SKU pindah ke bucket lebih rendah (PI turun)
""")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5 — BL CATEGORIZATION
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header" id="business-line">5️⃣ Business Line (BL) Categorization</div>',
            unsafe_allow_html=True)

st.markdown("""
##### Pricing BL 2025 → 4 Segments

Engine kategorize semua SKU ke **4 Business Lines** untuk pricing analysis berdasarkan L1 + business_lines_2025:

| Segment | Rule | Examples |
|---|---|---|
| **Frozen** | L1 mengandung `ayam`, `unggas`, `seafood`, `daging beku` | Ayam Beku, Sosis & Nugget, Es Krim |
| **Fresh** | L1 mengandung `buah`, `sayur`, `telur`, `tahu`, `tempe` | Sayuran Hijau, Buah Tropis, Tahu & Tempe, Telur Ayam |
| **PL** (Private Label) | business_lines_2025 mengandung `ab`, `ag`, `ak` | Private Label products |
| **Dry** | business_lines_2025 mengandung `dry food` atau `dry non food` | Snack, Mi Instan, Personal Care, Pembersih Rumah |
| **Others** | Sisa SKU yang gak match rule di atas | Edge cases |

**Why segments:** Pricing strategy beda per segment — Fresh punya elastisitas tinggi,
Frozen lebih sensitive ke PI, Dry lebih stable, PL punya margin paling tinggi.

##### Decomposition Scope

Semua analysis decomposition (PVM, PI) menampilkan:
- **Overall** — semua SKU
- Filter scope: **Dry**, **Fresh**, **Frozen**, **PL** (di Page 1)
- Filter scope: **Dry**, **Fresh**, **Frozen** (di Page 2)
""")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6 — ACRONYMS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header" id="acronyms">6️⃣ Acronyms & Glossary</div>', unsafe_allow_html=True)

st.markdown("""
| Acronym | Meaning |
|---|---|
| **PI** | Pricing Index |
| **PVM** | Price × Volume × Mix |
| **GP** | Gross Profit |
| **GV** | Goods Value (= net sales / revenue) |
| **CI** | COGS Index |
| **COGS** | Cost of Goods Sold (a.k.a. HPP — Harga Pokok Produksi) |
| **AOV** | Average Order Value |
| **CM1 / CM2 / CM2.5** | Contribution Margin level 1 / 2 / 2.5 |
| **BL** | Business Line |
| **PL** | Private Label |
| **P1** | Period 1 (baseline, earlier period) |
| **P2** | Period 2 (current, later period) |
| **A** | Avg PI Prev (baseline, P1) |
| **E** | Avg PI Cur (result, P2) |
| **Δ (delta)** | Change between P1 and P2 |
| **pp** | Percentage point (used for margin% deltas) |
| **eff_*** | Effect component (eff_dep, eff_price, eff_comp, eff_new, etc.) |
| **w_ex / w_cur / w_nxt** | Weighting factor for Existing / Current / Next SKU count |
| **SKU** | Stock Keeping Unit (= product variant) |
| **OOS** | Out of Stock |
| **Comp** | Competitor (blended; effective comp price) |
| **Normal Comp** | Competitor price without any promo |
| **Discount Comp** | Competitor price with promo (= blended − normal) |

---

##### Period Convention

- **P1** = Period 1 = **Prev** (week_key di engine)
- **P2** = Period 2 = **Cur / Next** (next_week di engine)

Order: P1 → P2 (earlier → later in time).

---

##### Color Coding di Dashboard

| Color | Meaning |
|---|---|
| 🟢 Green | Positive movement (GP naik, margin naik, PI turun = lebih kompetitif) |
| 🔴 Red | Negative movement (GP turun, margin turun, PI naik = lebih mahal vs comp) |
| 🟡 Yellow | Match / neutral (PI sekitar 100, stay di bucket sama) |
| ⚫ Grey | Reference rows (Baseline, Result) atau missing data |

Gradient intensity = magnitude relatif ke max absolute value di table.
""")

st.markdown("---")
st.caption("📝 Glossary ini auto-updated kalau ada penambahan metric atau metodologi di engine. "
           "Source: `pvm_analyzer_v3.py` dan `pi_analyzer_v1.py`.")
