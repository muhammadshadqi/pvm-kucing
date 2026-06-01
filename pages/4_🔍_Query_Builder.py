"""
Query Builder — Page 4 (Pricing Toolkit)
Generate parameterized SQL queries for PVM and PI analysis.

Author: Shadqi (Pricing Strategy Analyst)
"""
import streamlit as st
from brand import inject_brand, render_brand_header
import datetime as dt
import calendar
import re

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Query Builder — Pricing",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="auto",
)

inject_brand()

# ─────────────────────────────────────────────────────────────────────────────
# QUERY TEMPLATES (placeholders: __WEEKDAY__, __START_DATE__, __END_DATE__)
# ─────────────────────────────────────────────────────────────────────────────

PVM_QUERY_TEMPLATE = """WITH 
date_dict as (
select
date('__START_DATE__') start_date,
date('__END_DATE__') end_date
)

  ,label AS (
  SELECT
    product_id,
    grouping_label,
  FROM
    `astro-data-prd.astro_google_sheet.temp_grouping_label_by_sku`
)

,raw_stock AS(
SELECT
  DISTINCT 
  DATE_TRUNC(DATE_ADD(main.date_key, INTERVAL 0 DAY), WEEK(__WEEKDAY__)) + 0 week_key,
  date_key,
  product_id,
  main.product_name,
  start_available_stock,
  FROM astro-data-prd.astro_datamart_supply_chain.rpt_overall_stock_movement AS main
  LEFT JOIN label USING (product_id)
  WHERE date_key BETWEEN (select distinct date(start_date) from date_dict) and (select distinct date(end_date) from date_dict)
)

,weekly_stock AS(
SELECT week_key, product_id, 
  AVG(start_available_stock) avg_stock
FROM (
    SELECT week_key, date_key, rm.product_id,
      SUM(IFNULL(start_available_stock,0)) AS start_available_stock,
    FROM raw_stock rm GROUP BY ALL
)
GROUP BY ALL
)

,raw1_dim_prod AS(
SELECT product_id, l1_category_name,
  `astro-data-prd.astro_function.business_lines_2025`(private_label_or_retail, pr.l1_category_name, pr.food_or_non_food, pr.product_type_name) business_lines_2025,
FROM `astro-data-prd.astro_dataset.dim_products_x_categories_x_attributes` pr
GROUP BY ALL 
) 

,dim_prod AS(SELECT product_id, 
CASE 
WHEN REGEXP_CONTAINS(LOWER(l1_category_name), r'ayam|unggas|seafood|daging beku') THEN 'Frozen'
WHEN REGEXP_CONTAINS(LOWER(l1_category_name), r'buah|sayur|telur|tahu|tempe') THEN 'Fresh'
WHEN REGEXP_CONTAINS(LOWER(business_lines_2025), r'ab|ag|ak') THEN 'PL'
WHEN REGEXP_CONTAINS(LOWER(business_lines_2025), r'dry food|dry non food') THEN 'Dry'
ELSE 'Others'
END AS pricing_bl_25,
FROM raw1_dim_prod GROUP BY ALL)

,pareto AS(
SELECT product_id, pareto_classification
FROM astro-data-prd.astro_datamart_commercial.fact_pareto_per_product_x_sku_scoring_astro_level_qcom
WHERE 1=1 
AND month_key = DATE_TRUNC((select distinct date(end_date) from date_dict),MONTH)
GROUP BY ALL 
) 

,raw_main AS(
  SELECT
  DATE_TRUNC(date_key,MONTH) month_key, 
  DATE_TRUNC(DATE_ADD(date_key, INTERVAL 0 DAY), WEEK(__WEEKDAY__)) + 0 week_key,
  date_key, product_id, 
  comp_price_mapping comp_price,
FROM astro-data-prd.astro_datamart_buyer_exp.rpt_pricing_suggested_price_simulation
LEFT JOIN dim_prod USING(product_id)
WHERE date_key between (select distinct date(start_date) from date_dict) and (select distinct date(end_date) from date_dict)
AND pi <> 0 AND converted_type = 'exact match' AND pi IS NOT NULL AND pricing_bl_25 = 'Dry'
GROUP BY ALL

UNION ALL 

  SELECT
  DATE_TRUNC(date_key,MONTH) month_key, 
  DATE_TRUNC(DATE_ADD(date_key, INTERVAL 0 DAY), WEEK(__WEEKDAY__)) + 0 week_key,
  date_key, product_id, 
  comp_price_mapping comp_price,
FROM astro-data-prd.astro_datamart_buyer_exp.rpt_pricing_suggested_price_simulation
LEFT JOIN dim_prod USING(product_id)
WHERE date_key between (select distinct date(start_date) from date_dict) and (select distinct date(end_date) from date_dict)
AND pi <> 0 AND converted_type = 'overall' AND pi IS NOT NULL AND pricing_bl_25 IN ('Fresh','Frozen')
GROUP BY ALL
)

,main AS(SELECT week_key, product_id, AVG(comp_price) comp_price FROM raw_main GROUP BY ALL)

,raw_rpt as (
  select distinct
  DATE_TRUNC(DATE_ADD(a.date_key, INTERVAL 0 DAY), WEEK(__WEEKDAY__)) + 0 week_key,
    a.product_id, a.product_name, pricing_bl_25, l1_category_name, business_lines_2025,
    comp_price, 
    SUM(a.goods_value) goods_value, SUM(a.quantity_sold) AS qty, SUM(total_cogs) cogs,
    SAFE_DIVIDE(SUM(goods_value), SUM(a.quantity_sold)) AS selling_price,
    SAFE_DIVIDE(SUM(total_cogs), SUM(a.quantity_sold)) AS cost_price,
  from astro-data-prd.astro_datamart.rpt_gross_margin a
  LEFT JOIN dim_prod dp ON a.product_id = dp.product_id
  LEFT JOIN main r ON a.product_id = r.product_id AND DATE_TRUNC(DATE_ADD(a.date_key, INTERVAL 0 DAY), WEEK(__WEEKDAY__)) + 0 = r.week_key
  where a.date_key between (select distinct date(start_date) from date_dict) and (select distinct date(end_date) from date_dict)
  and order_id_sales is not null and a.goods_value > 0 and a.location_type = 'overall'
  and order_type not in ('KITCHEN')
  GROUP BY ALL
)

,list_prod AS(
  SELECT product_id, product_name, pricing_bl_25, l1_category_name, business_lines_2025,
  FROM raw_rpt 
  WHERE week_key IN(
    DATE_TRUNC(DATE_ADD((SELECT DATE(start_date) FROM date_dict LIMIT 1),INTERVAL 0 DAY),WEEK(__WEEKDAY__)),
    DATE_TRUNC(DATE_ADD((SELECT DATE(end_date) FROM date_dict LIMIT 1),INTERVAL 0 DAY),WEEK(__WEEKDAY__))
  )
  GROUP BY ALL
)

SELECT 
DATE_TRUNC(DATE_ADD((SELECT DATE(start_date) FROM date_dict LIMIT 1),INTERVAL 0 DAY),WEEK(__WEEKDAY__)) AS week_key,
DATE_TRUNC(DATE_ADD((SELECT DATE(end_date) FROM date_dict LIMIT 1),INTERVAL 0 DAY),WEEK(__WEEKDAY__)) AS next_week,
l.*, pareto_classification,
a.qty, b.qty AS qty1,
a.selling_price, b.selling_price AS selling_price1,
a.cost_price, b.cost_price AS cost_price1,
SAFE_DIVIDE(a.selling_price-a.cost_price,a.selling_price) AS margin_pct,
SAFE_DIVIDE(b.selling_price-b.cost_price,b.selling_price) AS margin1_pct,
a.comp_price, b.comp_price AS comp_price1,
SAFE_DIVIDE(a.selling_price*100,a.comp_price) AS pi,
SAFE_DIVIDE(b.selling_price*100,b.comp_price) AS pi1,
c.avg_stock, d.avg_stock AS avg_stock1,
FROM list_prod l
LEFT JOIN (SELECT * FROM raw_rpt WHERE week_key = DATE_TRUNC(DATE_ADD((SELECT DATE(start_date) FROM date_dict LIMIT 1),INTERVAL 0 DAY),WEEK(__WEEKDAY__))) a USING(product_id) 
LEFT JOIN (SELECT * FROM raw_rpt WHERE week_key = DATE_TRUNC(DATE_ADD((SELECT DATE(end_date) FROM date_dict LIMIT 1),INTERVAL 0 DAY),WEEK(__WEEKDAY__))) b USING(product_id) 
LEFT JOIN (SELECT * FROM weekly_stock WHERE week_key = DATE_TRUNC(DATE_ADD((SELECT DATE(start_date) FROM date_dict LIMIT 1),INTERVAL 0 DAY),WEEK(__WEEKDAY__))) c USING(product_id) 
LEFT JOIN (SELECT * FROM weekly_stock WHERE week_key = DATE_TRUNC(DATE_ADD((SELECT DATE(end_date) FROM date_dict LIMIT 1),INTERVAL 0 DAY),WEEK(__WEEKDAY__))) d USING(product_id) 
LEFT JOIN pareto USING(product_id)
"""


PI_QUERY_TEMPLATE = """WITH date_dict as (
select date('__START_DATE__') start_date, date('__END_DATE__') end_date
)

,cogs_date as (
select distinct product_id, cogs, date_key 
from astro_dataset.fact_cogs_per_product_per_date 
where date_key between (select distinct date(start_date) from date_dict) and (select distinct date(end_date) from date_dict)
)

,raw_price AS(
SELECT date_key, product_id, price_full_final AS price
FROM `astro-data-prd.astro_dataset.fact_mode_price_per_product_daily`
WHERE date_key between (select distinct date(start_date) from date_dict) and (select distinct date(end_date) from date_dict)
AND price_full_final <> 0 AND price_full_final IS NOT NULL
GROUP BY ALL
)

,raw1_dim_prod AS(
SELECT product_id, l1_category_name, product_name, source_status,
  `astro-data-prd.astro_function.business_lines_2025`(private_label_or_retail, pr.l1_category_name, pr.food_or_non_food, pr.product_type_name) business_lines_2025,
FROM `astro-data-prd.astro_dataset.dim_products_x_categories_x_attributes` pr
GROUP BY ALL 
) 

,dim_prod AS(SELECT product_id, l1_category_name, product_name, source_status,
CASE 
WHEN REGEXP_CONTAINS(LOWER(l1_category_name), r'ayam|unggas|seafood|daging beku') THEN 'Frozen'
WHEN REGEXP_CONTAINS(LOWER(l1_category_name), r'buah|sayur|telur|tahu|tempe') THEN 'Fresh'
WHEN REGEXP_CONTAINS(LOWER(business_lines_2025), r'ab|ag|ak') THEN 'PL'
WHEN REGEXP_CONTAINS(LOWER(business_lines_2025), r'dry food|dry non food') THEN 'Dry'
ELSE 'Others'
END AS pricing_bl_25,
FROM raw1_dim_prod GROUP BY ALL)

,pareto AS(
SELECT product_id, pareto_classification
FROM astro-data-prd.astro_datamart_commercial.fact_pareto_per_product_x_sku_scoring_astro_level_qcom
WHERE 1=1 AND month_key = DATE_TRUNC((select distinct date(end_date) from date_dict),MONTH)
GROUP BY ALL 
) 

-----------------------------------------------|| Comp Normal Price ||-----------------------------------------------------------------------

,raw_normal_comp AS(  
SELECT DATE_TRUNC(date_key,MONTH) month_key, date_key,
  DATE_TRUNC(DATE_ADD(date_key, INTERVAL 0 DAY), WEEK(__WEEKDAY__)) + 0 week_key,
  product_id,
  comp_price_mapping,
FROM astro-data-prd.astro_datamart_buyer_exp.fact_competitor_normal_price_per_pricing_product_type  
LEFT JOIN dim_prod dp USING(product_id)
WHERE date_key between (select distinct date(start_date) from date_dict) and (select distinct date(end_date) from date_dict)
AND comp_price_mapping <> 0 AND comp_price_mapping IS NOT NULL
AND converted_type = 'overall' AND dp.source_status = 'SOURCE' AND pricing_bl_25 NOT IN ('PL','Dry')
GROUP BY ALL

UNION ALL    

SELECT DATE_TRUNC(date_key,MONTH) month_key, date_key,
  DATE_TRUNC(DATE_ADD(date_key, INTERVAL 0 DAY), WEEK(__WEEKDAY__)) + 0 week_key,
  product_id,
  comp_price_mapping,
FROM astro-data-prd.astro_datamart_buyer_exp.rpt_pricing_suggested_price_simulation  
LEFT JOIN dim_prod dp USING(product_id)
LEFT JOIN cogs_date c USING(product_id,date_key)
WHERE date_key between (select distinct date(start_date) from date_dict) and (select distinct date(end_date) from date_dict)
AND pi <> 0 AND pi IS NOT NULL AND converted_type = 'exact match' AND dp.source_status = 'SOURCE' AND pricing_bl_25 IN ('Dry')
GROUP BY ALL
)

,main_normal_comp AS(SELECT week_key, product_id, AVG(comp_price_mapping) normal_comp_price FROM raw_normal_comp GROUP BY ALL)

-----------------------------------------------|| Comp Price blended ||-----------------------------------------------------------------------
,raw_main AS(  
SELECT DATE_TRUNC(date_key,MONTH) month_key, date_key,
  DATE_TRUNC(DATE_ADD(date_key, INTERVAL 0 DAY), WEEK(__WEEKDAY__)) + 0 week_key,
  product_id, dp.product_name, dp.l1_category_name, dp.source_status, pricing_bl_25,
  selling_price AS price, c.cogs, comp_price_mapping comp_price,
FROM astro-data-prd.astro_datamart_buyer_exp.rpt_pricing_suggested_price_simulation  
LEFT JOIN dim_prod dp USING(product_id)
LEFT JOIN cogs_date c USING(product_id,date_key)
WHERE date_key between (select distinct date(start_date) from date_dict) and (select distinct date(end_date) from date_dict)
AND pi <> 0 AND pi IS NOT NULL AND converted_type = 'overall' AND dp.source_status = 'SOURCE' AND pricing_bl_25 NOT IN ('PL','Dry')
GROUP BY ALL

UNION ALL    

SELECT DATE_TRUNC(date_key,MONTH) month_key, date_key,
  DATE_TRUNC(DATE_ADD(date_key, INTERVAL 0 DAY), WEEK(__WEEKDAY__)) + 0 week_key,
  product_id, dp.product_name, dp.l1_category_name, dp.source_status, pricing_bl_25,
  selling_price AS price, c.cogs, comp_price_mapping comp_price,
FROM astro-data-prd.astro_datamart_buyer_exp.rpt_pricing_suggested_price_simulation  
LEFT JOIN dim_prod dp USING(product_id)
LEFT JOIN cogs_date c USING(product_id,date_key)
WHERE date_key between (select distinct date(start_date) from date_dict) and (select distinct date(end_date) from date_dict)
AND pi <> 0 AND pi IS NOT NULL AND converted_type = 'exact match' AND dp.source_status = 'SOURCE' AND pricing_bl_25 IN ('Dry')
GROUP BY ALL
)

,main1 AS(SELECT week_key, product_id, product_name, l1_category_name, source_status, pricing_bl_25,
  AVG(price) price, AVG(cogs) cogs, AVG(comp_price) comp_price FROM raw_main GROUP BY ALL)

,main AS(SELECT week_key, product_id, product_name, l1_category_name, source_status, pricing_bl_25,
  price, cogs, SAFE_DIVIDE(price-cogs,price) gp_pct, comp_price,
  SAFE_DIVIDE(price*100,comp_price) pi, SAFE_DIVIDE(cogs*100,comp_price) cogs_index, normal_comp_price
FROM main1  
LEFT JOIN main_normal_comp  
USING(product_id,week_key)  
)

,dict AS(SELECT product_id, product_name, l1_category_name, source_status, pricing_bl_25 FROM main GROUP BY ALL)

SELECT
DATE_TRUNC(DATE_ADD((SELECT DATE(start_date) FROM date_dict LIMIT 1),INTERVAL 0 DAY),WEEK(__WEEKDAY__)) week_key,
DATE_TRUNC(DATE_ADD((SELECT DATE(end_date) FROM date_dict LIMIT 1),INTERVAL 0 DAY),WEEK(__WEEKDAY__)) next_week,
d.product_id, d.product_name, d.l1_category_name, d.source_status, d.pricing_bl_25, pareto_classification,
m1.price, m2.price AS next_price,
m1.cogs, m2.cogs AS next_cogs,
m1.comp_price, m2.comp_price AS next_comp_price,
m1.pi, m2.pi AS next_pi,
m1.normal_comp_price AS normal_comp_price, m2.normal_comp_price AS next_normal_comp_price
FROM dict d
LEFT JOIN (SELECT * FROM main m2 WHERE week_key = DATE_TRUNC(DATE_ADD((SELECT DATE(start_date) FROM date_dict LIMIT 1),INTERVAL 0 DAY),WEEK(__WEEKDAY__))) m1 ON m1.product_id = d.product_id
LEFT JOIN (SELECT * FROM main m2 WHERE week_key = DATE_TRUNC(DATE_ADD((SELECT DATE(end_date) FROM date_dict LIMIT 1),INTERVAL 0 DAY),WEEK(__WEEKDAY__))) m2 ON d.product_id = m2.product_id 
LEFT JOIN pareto p ON d.product_id = p.product_id
"""


# ═══════════════════════════════════════════════════════════════════════════
# PAGE 3 QUERY TEMPLATE — single date range, no weekday picker
# Placeholders: __START_DATE__, __END_DATE__
# ═══════════════════════════════════════════════════════════════════════════
PAGE3_QUERY_TEMPLATE = """WITH 
date_dict as (
select
date('__START_DATE__') start_date,
date('__END_DATE__') end_date
)

,raw1_dim_prod AS(
SELECT product_id, product_name, l1_category_name, l2_category_name,
  `astro-data-prd.astro_function.business_lines_2025`(private_label_or_retail, pr.l1_category_name, pr.food_or_non_food, pr.product_type_name) business_lines_2025,
FROM `astro-data-prd.astro_dataset.dim_products_x_categories_x_attributes` pr
GROUP BY ALL 
) 

,dim_prod AS(SELECT product_id,
CASE 
WHEN REGEXP_CONTAINS(LOWER(l1_category_name), r'ayam|unggas|seafood|daging beku') THEN 'Frozen'
WHEN REGEXP_CONTAINS(LOWER(l1_category_name), r'buah|sayur|telur|tahu|tempe') THEN 'Fresh'
WHEN REGEXP_CONTAINS(LOWER(business_lines_2025), r'ab|ag|ak') THEN 'PL'
WHEN REGEXP_CONTAINS(LOWER(business_lines_2025), r'dry food|dry non food') THEN 'Dry'
ELSE 'Others'
END AS pricing_bl_25,
product_name, l1_category_name, l2_category_name,
FROM raw1_dim_prod GROUP BY ALL
)


-------------------------------|| Comp Price Blended ||---------------------------------------------
,raw_main AS(  
SELECT DATE_TRUNC(date_key,MONTH) month_key, date_key,
  DATE_TRUNC(DATE_ADD(date_key, INTERVAL 0 DAY), WEEK(MONDAY)) + 0 week_key,
  product_id, dp.product_name, dp.l1_category_name, pricing_bl_25,
  selling_price AS price,  comp_price_mapping comp_price,
FROM astro-data-prd.astro_datamart_buyer_exp.rpt_pricing_suggested_price_simulation  
LEFT JOIN dim_prod dp USING(product_id)
WHERE date_key between (select distinct date(start_date) from date_dict) and (select distinct date(end_date) from date_dict)
AND pi <> 0 AND pi IS NOT NULL AND converted_type = 'overall'  AND pricing_bl_25 NOT IN ('PL','Dry')
GROUP BY ALL

UNION ALL    

SELECT DATE_TRUNC(date_key,MONTH) month_key, date_key,
  DATE_TRUNC(DATE_ADD(date_key, INTERVAL 0 DAY), WEEK(MONDAY)) + 0 week_key,
  product_id, dp.product_name, dp.l1_category_name, pricing_bl_25,
  selling_price AS price, comp_price_mapping comp_price,
FROM astro-data-prd.astro_datamart_buyer_exp.rpt_pricing_suggested_price_simulation  
LEFT JOIN dim_prod dp USING(product_id)
WHERE date_key between (select distinct date(start_date) from date_dict) and (select distinct date(end_date) from date_dict)
AND pi <> 0 AND pi IS NOT NULL AND converted_type = 'exact match'  AND pricing_bl_25 IN ('Dry')
GROUP BY ALL
)

,avg_comp_price AS(SELECT product_id,
  AVG(price) price, AVG(comp_price) comp_price FROM raw_main GROUP BY ALL)

,last_day_comp_price AS(SELECT date_key, product_id,
  price price, comp_price comp_price FROM raw_main QUALIFY ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY date_key DESC) = 1)




,pnl AS(
SELECT DISTINCT
    a.product_id, dp.product_name, dp.l1_category_name, dp.l2_category_name,
    pricing_bl_25,
    SUM(a.quantity_sold) AS qty,
    SAFE_DIVIDE(SUM(goods_value), SUM(a.quantity_sold)) AS selling_price,
    SAFE_DIVIDE(SUM(total_cogs), SUM(a.quantity_sold)) AS cost_price,
FROM astro-data-prd.astro_datamart.rpt_gross_margin a
LEFT JOIN dim_prod dp ON a.product_id = dp.product_id
WHERE a.date_key BETWEEN (SELECT DATE(start_date) FROM date_dict) AND (SELECT DATE(end_date) FROM date_dict)
AND order_id_sales is not null AND a.goods_value > 0
AND a.location_type = 'overall' AND order_type not in ('KITCHEN')
GROUP BY ALL
)

SELECT 
product_id, 
product_name ,
l1_category_name,
l2_category_name, 
pricing_bl_25,
qty,
selling_price,
cost_price, 
b.comp_price AS avg_comp_price, 
c.comp_price AS last_comp_price,
c.price AS last_price

FROM pnl a
LEFT JOIN avg_comp_price b
USING(product_id)
LEFT JOIN last_day_comp_price c
USING(product_id)
"""


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

# Python's calendar.weekday(): Mon=0, Tue=1, ..., Sun=6
WEEKDAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
WEEKDAY_BIGQUERY = {  # Python idx -> BigQuery WEEK() keyword
    0: 'MONDAY',
    1: 'TUESDAY',
    2: 'WEDNESDAY',
    3: 'THURSDAY',
    4: 'FRIDAY',
    5: 'SATURDAY',
    6: 'SUNDAY',
}

def list_dates_with_weekday(year, month, weekday_idx):
    """Return all dates in (year, month) that fall on the given weekday."""
    cal = calendar.Calendar()
    return [d for d in cal.itermonthdates(year, month)
            if d.month == month and d.weekday() == weekday_idx]


def render_date_range_query(query_label, query_template, key_prefix):
    """Render UI for queries that need ONLY a start_date and end_date (no weekday picker)."""

    st.markdown(f"##### ⚙️ Konfigurasi {query_label}")

    today = dt.date.today()
    default_start = (today - dt.timedelta(days=30)).replace(day=1)  # 1st of last month
    default_end = today

    c1, c2 = st.columns(2)
    with c1:
        start_date = st.date_input(
            "Start Date:",
            value=default_start,
            key=f'{key_prefix}_start_dr',
            help="Tanggal awal range"
        )
    with c2:
        end_date = st.date_input(
            "End Date:",
            value=default_end,
            key=f'{key_prefix}_end_dr',
            help="Tanggal akhir range"
        )

    # Validation
    if end_date < start_date:
        st.error(f"❌ End Date ({end_date}) harus ≥ Start Date ({start_date})")
        return

    n_days = (end_date - start_date).days + 1

    # Preview
    st.markdown('<div class="info-box">', unsafe_allow_html=True)
    st.markdown(
        f"📌 **Preview parameters:**<br>"
        f"• Start Date: <code>{start_date.strftime('%Y-%m-%d')}</code><br>"
        f"• End Date: <code>{end_date.strftime('%Y-%m-%d')}</code><br>"
        f"• Range total: <code>{n_days}</code> hari",
        unsafe_allow_html=True
    )
    st.markdown('</div>', unsafe_allow_html=True)

    # Generate query
    generated_sql = (
        query_template
        .replace('__START_DATE__', start_date.strftime('%Y-%m-%d'))
        .replace('__END_DATE__', end_date.strftime('%Y-%m-%d'))
    )

    st.markdown("##### 📝 Generated SQL Query")
    st.caption("Hover pada code block → klik icon copy (📋) di pojok kanan atas untuk salin query.")
    st.code(generated_sql, language='sql')

    n_lines = len(generated_sql.splitlines())
    n_chars = len(generated_sql)
    st.caption(f"📊 {n_lines:,} lines · {n_chars:,} characters")


def render_query_builder(query_label, query_template, key_prefix):
    """Render the query builder UI for a single query template."""

    # ── Inputs ──
    st.markdown(f"##### ⚙️ Konfigurasi {query_label}")

    # Row 1: Weekday picker
    col_wd, col_year_s, col_month_s = st.columns([2, 1, 1])
    with col_wd:
        weekday_choice = st.selectbox(
            "Hari Week Start:",
            options=list(range(7)),
            format_func=lambda i: WEEKDAY_NAMES[i],
            index=0,  # default Monday
            key=f'{key_prefix}_weekday',
            help="Hari yang dipakai sebagai awal minggu (mapped ke WEEK(<DAY>) di SQL)"
        )

    # ── Start Week section ──
    st.markdown("**Start Week (Period 1):**")
    col_year_s, col_month_s, col_date_s = st.columns([1, 1, 2])
    current_year = dt.date.today().year
    with col_year_s:
        year_s = st.selectbox(
            "Tahun:",
            options=list(range(current_year - 2, current_year + 3)),
            index=2,
            key=f'{key_prefix}_year_s'
        )
    with col_month_s:
        month_s = st.selectbox(
            "Bulan:",
            options=list(range(1, 13)),
            format_func=lambda m: calendar.month_name[m],
            index=dt.date.today().month - 1,
            key=f'{key_prefix}_month_s'
        )
    with col_date_s:
        valid_dates_s = list_dates_with_weekday(year_s, month_s, weekday_choice)
        if not valid_dates_s:
            st.error(f"⚠️ Tidak ada {WEEKDAY_NAMES[weekday_choice]} di {calendar.month_name[month_s]} {year_s}")
            start_date = None
        else:
            start_date = st.selectbox(
                f"Tanggal ({WEEKDAY_NAMES[weekday_choice]}):",
                options=valid_dates_s,
                format_func=lambda d: d.strftime('%Y-%m-%d (%a)'),
                key=f'{key_prefix}_start'
            )

    # ── Next Week section ──
    st.markdown("**Next Week (Period 2):**")
    col_year_n, col_month_n, col_date_n = st.columns([1, 1, 2])
    with col_year_n:
        year_n = st.selectbox(
            "Tahun:",
            options=list(range(current_year - 2, current_year + 3)),
            index=2,
            key=f'{key_prefix}_year_n'
        )
    with col_month_n:
        month_n = st.selectbox(
            "Bulan:",
            options=list(range(1, 13)),
            format_func=lambda m: calendar.month_name[m],
            index=dt.date.today().month - 1,
            key=f'{key_prefix}_month_n'
        )
    with col_date_n:
        valid_dates_n = list_dates_with_weekday(year_n, month_n, weekday_choice)
        if not valid_dates_n:
            st.error(f"⚠️ Tidak ada {WEEKDAY_NAMES[weekday_choice]} di {calendar.month_name[month_n]} {year_n}")
            next_date = None
        else:
            next_date = st.selectbox(
                f"Tanggal ({WEEKDAY_NAMES[weekday_choice]}):",
                options=valid_dates_n,
                format_func=lambda d: d.strftime('%Y-%m-%d (%a)'),
                key=f'{key_prefix}_next'
            )

    # ── Validation ──
    if start_date is None or next_date is None:
        st.warning("⚠️ Pilih tanggal yang valid untuk Start Week dan Next Week dulu.")
        return

    if next_date < start_date:
        st.error(f"❌ Next Week ({next_date}) harus ≥ Start Week ({start_date})")
        return

    # ── Compute end_date (next_date + 6 days) ──
    end_date = next_date + dt.timedelta(days=6)

    # ── Preview ──
    st.markdown('<div class="info-box">', unsafe_allow_html=True)
    st.markdown(
        f"📌 **Preview parameters:**<br>"
        f"• Weekday for `WEEK()`: <code>{WEEKDAY_BIGQUERY[weekday_choice]}</code><br>"
        f"• Start Date (P1): <code>{start_date.strftime('%Y-%m-%d')}</code> ({WEEKDAY_NAMES[weekday_choice]})<br>"
        f"• Next Week starts: <code>{next_date.strftime('%Y-%m-%d')}</code> ({WEEKDAY_NAMES[weekday_choice]})<br>"
        f"• End Date (P2 + 6 days): <code>{end_date.strftime('%Y-%m-%d')}</code> ({WEEKDAY_NAMES[end_date.weekday()]})<br>"
        f"• Range total: <code>{(end_date - start_date).days + 1}</code> hari",
        unsafe_allow_html=True
    )
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Generate query ──
    bq_weekday = WEEKDAY_BIGQUERY[weekday_choice]
    generated_sql = (
        query_template
        .replace('__WEEKDAY__', bq_weekday)
        .replace('__START_DATE__', start_date.strftime('%Y-%m-%d'))
        .replace('__END_DATE__', end_date.strftime('%Y-%m-%d'))
    )

    # ── Display ──
    st.markdown("##### 📝 Generated SQL Query")
    st.caption(f"Hover pada code block → klik icon copy (📋) di pojok kanan atas untuk salin query.")
    st.code(generated_sql, language='sql')

    # Stats
    n_lines = len(generated_sql.splitlines())
    n_chars = len(generated_sql)
    st.caption(f"📊 {n_lines:,} lines · {n_chars:,} characters")


# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────
render_brand_header("Query Builder", "Generate parameterized SQL queries untuk BigQuery")

st.markdown("""
**How to use:**
1. Pilih tab sesuai jenis analisis (PVM / PI / Page 3)
2. Pilih hari Week Start (Monday / Tuesday / dst) — akan otomatis update `WEEK(<DAY>)` di query
3. Pilih Tahun + Bulan + Tanggal untuk **Start Week** (Period 1)
4. Pilih Tahun + Bulan + Tanggal untuk **Next Week** (Period 2)
5. Query auto-generate dengan substitution:
   - `WEEK(MONDAY)` → `WEEK(<hari pilihan>)`
   - `start_date` → tanggal Start Week
   - `end_date` → tanggal Next Week + 6 hari
6. Hover code block → klik ikon copy di pojok kanan atas
""")

# ─────────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────────
tab_pvm, tab_pi, tab_p3 = st.tabs([
    "📊 Query 1 — PVM",
    "📈 Query 2 — PI",
    "📅 Query 3 — Page 3 (Date Range)"
])

with tab_pvm:
    st.markdown('<div class="section-header">📊 PVM Query</div>', unsafe_allow_html=True)
    st.caption("Query untuk Page 1 — PVM Analyzer. Output: per-SKU per-week data dengan margin, "
               "quantity, comp_price, PI, dan avg_stock untuk 2 periode comparison.")
    render_query_builder("PVM", PVM_QUERY_TEMPLATE, "pvm")

with tab_pi:
    st.markdown('<div class="section-header">📈 PI Query</div>', unsafe_allow_html=True)
    st.caption("Query untuk Page 2 — PI Analyzer. Output: per-SKU per-week data dengan "
               "price, COGS, comp_price (blended + normal), PI untuk 2 periode comparison.")
    render_query_builder("PI", PI_QUERY_TEMPLATE, "pi")

with tab_p3:
    st.markdown('<div class="section-header">📅 Page 3 Query — Date Range Analysis</div>', unsafe_allow_html=True)
    st.caption(
        "Query untuk Page 3. Berbeda dari Query 1 & 2: cuma 1 periode (date range) "
        "dengan output `qty`, `selling_price`, `cost_price`, `avg_comp_price`, `last_comp_price`, dan `last_price`. "
        "Cocok untuk monthly/quarterly analysis per SKU."
    )
    render_date_range_query("Page 3", PAGE3_QUERY_TEMPLATE, "p3")
