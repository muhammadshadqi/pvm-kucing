# 📊 PVM Analyzer — Astro Pricing Strategy

Streamlit web app untuk analisis **Pricing × Volume × Mix (PVM)** decomposition pada week-over-week atau month-over-month pricing data. Replicate full logic dari `pvm_analyzer_v3.py` ke interactive UI.

## ✨ Fitur Page 1

- **📁 Upload zone** dengan validation panel, preview, dan template download
- **⚠️ Anomaly banner** auto-detect BL dengan GP drop > 3% atau GV drop > 4%
- **📈 Executive KPI strip** (GV, GP, Margin, Qty, # SKU, SKU Churn)
- **🌊 Margin Bridge waterfall** dengan toggle scope (Overall/Dry/Fresh/Frozen/PL) dan toggle unit (Rp vs pp)
- **🔍 L1 Category breakdown** dengan filter per BL
- **🔝 Top 10 Movers** (gainers + losers) dengan kolom driver kosong (editable manual)
- **🎯 SKU Watch List Priority** dengan suggested action
- **💾 Download Full Excel** 12-sheet identical dengan `pvm_analyzer_v3.py` output

## 🚀 Run Locally

### 1. Setup environment

```bash
# Clone repo
git clone https://github.com/<username>/pvm-analyzer.git
cd pvm-analyzer

# Install dependencies
pip install -r requirements.txt
```

### 2. Jalankan app

```bash
streamlit run app.py
```

Buka browser ke `http://localhost:8501`.

### 3. Upload file

Format input file sesuai `pvm_analyzer_v3.py`:

**Required cols:**
- `selling_price`, `selling_price1` (harga jual P1 vs P2)
- `cost_price`, `cost_price1` (COGS P1 vs P2)
- `qty`, `qty1` (qty sold P1 vs P2)

**Period cols (salah satu pair):**
- `week_key` + `next_week` (atau `next_key`)
- `month_key` + `next_month`

**Optional cols:** `comp_price`, `comp_price1`, `pi`, `pi1`, `avg_stock`, `avg_stock1`, `margin_pct`, `margin1_pct`, `pareto_classification`

**Dimension cols:** `pricing_bl_25`, `l1_category_name`, `business_lines_2025`, `product_id`, `product_name`

Klik **Download Template** di app untuk contoh format.

## ☁️ Deploy ke Streamlit Community Cloud

1. Push repo ke GitHub (public)
2. Login `https://share.streamlit.io` dengan GitHub
3. Klik **New app** → pilih repo → main file `app.py`
4. Deploy. App live di `https://<your-app>.streamlit.app`

## 📐 Margin Bridge — Custom Naming

App ini menggunakan custom naming convention sesuai brief:

| Step | Label |
|------|-------|
| Churned | **1. Churned SKU Effect** (formerly "Remove Deprecated") |
| Existing aggregate | **2. Existing SKU Effect** (sum of 2.1+2.2+2.3) |
| Cost effect | **  2.1 COGS Effect** |
| Price effect | **  2.2 Price Effect** |
| Vol/Mix residual | **  2.3 Vol/Mix Effect** |
| New SKU | **3. New SKU Effect** (formerly "Add New Products") |

Catatan: **Existing SKU Effect** adalah aggregate row — TIDAK dihitung lagi di total bridge sum (dihindari double-count).

## 📦 Output Excel — 12 Sheet

`{p1}_vs_{p2}_enriched.xlsx` mengandung:

1. `0. Formula Reference` — dokumentasi formula
2. `1. Raw Data` — per-SKU enriched (65 cols)
3. `Executive Overview` — summary KPI + bridge ringkas
4. `1b. Aggregates` — pre-computed numbers per BL (5 tables A-E)
5. `2. Margin Bridge` — full bridge
6. `2b. Margin Bridge (+-)` — waterfall (+) vs (-) split
7. `3. GV Tier Analysis` — breakdown by GV tier
8. `4. L1 Category Analysis` — L1 category breakdown
9. `5. New & Dep Analysis` — detail new & churned SKU
10. `6. COGS vs Comp Price` — pricing vs cost vs competitor
11. `6b. SKU Bermasalah` — flagged SKU
12. `7. SKU Watch List` — Priority / Review-Adjust / Framework Check

## 🛠️ Architecture

```
pvm_analyzer_app/
├── app.py                    # Streamlit UI (Page 1)
├── pvm_analyzer_v3.py        # Core PVM engine (callable via analyze())
├── requirements.txt          # Python dependencies
└── README.md
```

**Engine call:**

```python
from pvm_analyzer_v3 import analyze

result = analyze(df_input)
# result = {
#   'df': enriched_dataframe,
#   'pvm': dict_per_BL,
#   'excel_bytes': full_12_sheet_excel,
#   'p1': period_1_label,
#   'p2': period_2_label,
#   'meta': metadata
# }
```

## 🔒 Data Privacy

- Data hanya disimpan di `st.session_state` (browser session)
- **Tidak ada** data yang di-persist ke server
- Clear data manual via tombol **Clear data** atau tutup tab browser

## 📞 Contact

Built for Astro Pricing Strategy team.
