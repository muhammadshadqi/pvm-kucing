"""
Dummy Data Generator
Generates synthetic PVM and PI input data for default app preview.
Data is fully fictional — product names, IDs, and metrics are random.
"""
import numpy as np
import pandas as pd
import datetime as dt
import io


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS — fictional category structure
# ─────────────────────────────────────────────────────────────────────────────
DUMMY_L1_CATEGORIES = {
    'Dry': [
        'Snack & Krupuk', 'Makanan Instan', 'Minuman Botol', 'Bumbu Dapur',
        'Beras & Sereal', 'Susu Bubuk', 'Personal Hygiene', 'Pembersih Rumah',
        'Perlengkapan Bayi', 'Stationery',
    ],
    'Fresh': [
        'Sayuran Hijau', 'Buah Tropis', 'Tahu & Tempe', 'Telur Ayam',
        'Roti & Pastry',
    ],
    'Frozen': [
        'Ayam Beku', 'Seafood Beku', 'Daging Sapi', 'Sosis & Nugget',
        'Es Krim',
    ],
    'PL': [
        'Private Label Beverage', 'Private Label Snack',
    ],
}

# Pareto distribution: 5% A, 15% B, 30% C, 50% D
PARETO_PROBS = {'A': 0.05, 'B': 0.15, 'C': 0.30, 'D': 0.50}

SOURCE_STATUS_OPTIONS = ['SOURCE', 'NON SOURCE']


# Product name parts (fictional, generic)
ADJECTIVES = ['Prima', 'Surya', 'Mentari', 'Bintang', 'Sekar', 'Pelangi', 'Ceria',
              'Sehat', 'Segar', 'Alami', 'Sakti', 'Kencana', 'Jaya']
NOUNS = ['Manis', 'Spesial', 'Premium', 'Eko', 'Mini', 'Mega', 'Plus',
         'Original', 'Klasik', 'Sederhana']
SIZES = ['100g', '250g', '500g', '1kg', '200ml', '500ml', '1L',
         '6pcs', '12pcs', '1pc', '50g', '750ml']


# ─────────────────────────────────────────────────────────────────────────────
# PVM DUMMY (Page 1 input format)
# ─────────────────────────────────────────────────────────────────────────────
def generate_pvm_dummy(n_sku=600, seed=42):
    """
    Generate dummy PVM raw input matching the expected schema.

    Required cols by engine: selling_price, selling_price1, cost_price, cost_price1, qty, qty1
    Optional cols: comp_price, comp_price1, pi, pi1, avg_stock, avg_stock1,
                   pareto_classification, margin_pct, margin1_pct
    Dim cols: pricing_bl_25, l1_category_name, business_lines_2025
    Plus: product_id, product_name, week_key, next_week
    """
    rng = np.random.default_rng(seed)

    # Period anchors — last completed Monday vs prior Monday
    today = dt.date.today()
    days_since_monday = (today.weekday() - 0) % 7
    last_monday = today - dt.timedelta(days=days_since_monday + 7)
    prev_monday = last_monday - dt.timedelta(days=7)

    # BL distribution: Dry dominant (~60%), Fresh ~20%, Frozen ~15%, PL ~5%
    bl_weights = {'Dry': 0.60, 'Fresh': 0.20, 'Frozen': 0.15, 'PL': 0.05}

    rows = []
    for i in range(n_sku):
        # Pick BL based on weights
        bl = rng.choice(list(bl_weights.keys()), p=list(bl_weights.values()))
        l1 = rng.choice(DUMMY_L1_CATEGORIES[bl])

        # Generate product
        adj = rng.choice(ADJECTIVES)
        noun = rng.choice(NOUNS)
        size = rng.choice(SIZES)
        product_name = f"{adj} {noun} {size}"
        product_id = 100000 + i

        # Pareto class
        pareto = rng.choice(list(PARETO_PROBS.keys()), p=list(PARETO_PROBS.values()))

        # Price ranges differ by BL (realistic-ish)
        if bl == 'Fresh':
            base_price = rng.uniform(5000, 35000)
        elif bl == 'Frozen':
            base_price = rng.uniform(15000, 120000)
        elif bl == 'PL':
            base_price = rng.uniform(3000, 25000)
        else:  # Dry
            base_price = rng.uniform(5000, 80000)

        # Margin: 15-35% typical, with some loss leaders / high margins
        target_margin = rng.normal(0.22, 0.10)
        target_margin = max(-0.10, min(0.65, target_margin))  # clip
        cost_price = base_price * (1 - target_margin)

        # Period 2: small changes (±5%)
        price_change = rng.normal(0, 0.02)  # ±2% typical
        cost_change = rng.normal(0, 0.015)  # cost more stable
        selling_price1 = base_price * (1 + price_change)
        cost_price1 = cost_price * (1 + cost_change)

        # Quantity: random based on Pareto + noise
        pareto_qty_mult = {'A': 800, 'B': 250, 'C': 80, 'D': 20}
        qty_base = pareto_qty_mult[pareto] * (1 + rng.uniform(-0.3, 0.3))
        qty = int(max(0, qty_base))
        qty_change = rng.normal(0, 0.15)
        qty1 = int(max(0, qty_base * (1 + qty_change)))

        # Margin pct (recalculate to ensure consistency)
        margin_pct = (base_price - cost_price) / base_price if base_price > 0 else 0
        margin1_pct = (selling_price1 - cost_price1) / selling_price1 if selling_price1 > 0 else 0

        # Comp price: slightly above/below base price (±15% spread)
        if rng.uniform(0, 1) > 0.05:  # 95% have comp
            comp_price = base_price * (1 + rng.uniform(-0.15, 0.15))
            comp_price1 = comp_price * (1 + rng.normal(0, 0.02))
            pi = (base_price / comp_price) * 100 if comp_price > 0 else np.nan
            pi1 = (selling_price1 / comp_price1) * 100 if comp_price1 > 0 else np.nan
        else:
            comp_price = np.nan
            comp_price1 = np.nan
            pi = np.nan
            pi1 = np.nan

        # Stock
        avg_stock = int(rng.uniform(20, 800))
        # 8% chance of OOS in P2
        if rng.uniform(0, 1) < 0.08:
            avg_stock1 = 0
        else:
            avg_stock1 = int(avg_stock * (1 + rng.normal(0, 0.20)))

        # SKU type variance — small chance of new/departing
        churn_roll = rng.uniform(0, 1)
        if churn_roll < 0.02:  # 2% departing
            qty1 = 0
            selling_price1 = np.nan
            cost_price1 = np.nan
            margin1_pct = np.nan
            comp_price1 = np.nan
            pi1 = np.nan
            avg_stock1 = 0
        elif churn_roll < 0.04:  # 2% new
            qty = 0
            base_price = np.nan
            cost_price = np.nan
            margin_pct = np.nan
            comp_price = np.nan
            pi = np.nan
            avg_stock = 0

        rows.append({
            'week_key': prev_monday,
            'next_week': last_monday,
            'product_id': product_id,
            'product_name': product_name,
            'l1_category_name': l1,
            'pricing_bl_25': bl,
            'business_lines_2025': bl,
            'pareto_classification': pareto,
            'qty': qty,
            'qty1': qty1,
            'selling_price': base_price if pd.notna(base_price) else np.nan,
            'selling_price1': selling_price1 if pd.notna(selling_price1) else np.nan,
            'cost_price': cost_price if pd.notna(cost_price) else np.nan,
            'cost_price1': cost_price1 if pd.notna(cost_price1) else np.nan,
            'margin_pct': margin_pct,
            'margin1_pct': margin1_pct,
            'comp_price': comp_price,
            'comp_price1': comp_price1,
            'pi': pi,
            'pi1': pi1,
            'avg_stock': avg_stock,
            'avg_stock1': avg_stock1,
        })

    df = pd.DataFrame(rows)
    return df


# ─────────────────────────────────────────────────────────────────────────────
# PI DUMMY (Page 2 input format)
# ─────────────────────────────────────────────────────────────────────────────
def generate_pi_dummy(n_sku=600, seed=42):
    """
    Generate dummy PI raw input.

    Required cols: product_id, product_name, l1_category_name, pricing_bl_25,
                   pareto_classification, source_status,
                   price, next_price, cogs, next_cogs,
                   comp_price, next_comp_price,
                   normal_comp_price, next_normal_comp_price, pi, next_pi
    Plus period cols: week_key, next_week
    """
    rng = np.random.default_rng(seed)

    today = dt.date.today()
    days_since_monday = (today.weekday() - 0) % 7
    last_monday = today - dt.timedelta(days=days_since_monday + 7)
    prev_monday = last_monday - dt.timedelta(days=7)

    bl_weights = {'Dry': 0.60, 'Fresh': 0.20, 'Frozen': 0.15, 'PL': 0.05}

    rows = []
    for i in range(n_sku):
        bl = rng.choice(list(bl_weights.keys()), p=list(bl_weights.values()))
        l1 = rng.choice(DUMMY_L1_CATEGORIES[bl])
        adj = rng.choice(ADJECTIVES)
        noun = rng.choice(NOUNS)
        size = rng.choice(SIZES)
        product_name = f"{adj} {noun} {size}"
        product_id = 100000 + i

        pareto = rng.choice(list(PARETO_PROBS.keys()), p=list(PARETO_PROBS.values()))
        source_status = rng.choice(SOURCE_STATUS_OPTIONS, p=[0.75, 0.25])

        if bl == 'Fresh':
            base_price = rng.uniform(5000, 35000)
        elif bl == 'Frozen':
            base_price = rng.uniform(15000, 120000)
        elif bl == 'PL':
            base_price = rng.uniform(3000, 25000)
        else:
            base_price = rng.uniform(5000, 80000)

        target_margin = rng.normal(0.22, 0.10)
        target_margin = max(-0.10, min(0.65, target_margin))
        cogs = base_price * (1 - target_margin)

        price_change = rng.normal(0, 0.02)
        cogs_change = rng.normal(0, 0.015)
        next_price = base_price * (1 + price_change)
        next_cogs = cogs * (1 + cogs_change)

        # Comp prices — blended (with promos) vs normal (without promos)
        # comp_price = blended (usually lower bcs sometimes promos)
        # normal_comp_price = comp without any promo
        normal_comp = base_price * (1 + rng.uniform(-0.10, 0.20))  # tend slightly higher

        # Blended comp is normal comp with potential discount
        discount_chance = rng.uniform(0, 1)
        if discount_chance < 0.30:  # 30% have active promo
            discount_pct = rng.uniform(0.05, 0.30)
            comp_price = normal_comp * (1 - discount_pct)
        else:
            comp_price = normal_comp

        # Next period
        normal_comp_change = rng.normal(0, 0.02)
        next_normal_comp = normal_comp * (1 + normal_comp_change)

        next_discount_chance = rng.uniform(0, 1)
        if next_discount_chance < 0.30:
            next_discount_pct = rng.uniform(0.05, 0.30)
            next_comp_price = next_normal_comp * (1 - next_discount_pct)
        else:
            next_comp_price = next_normal_comp

        pi = (base_price / comp_price) * 100 if comp_price > 0 else np.nan
        next_pi_val = (next_price / next_comp_price) * 100 if next_comp_price > 0 else np.nan

        # SKU type variance
        churn_roll = rng.uniform(0, 1)
        if churn_roll < 0.025:  # departing
            next_price = np.nan
            next_cogs = np.nan
            next_comp_price = np.nan
            next_normal_comp = np.nan
            next_pi_val = np.nan
        elif churn_roll < 0.05:  # new
            base_price = np.nan
            cogs = np.nan
            comp_price = np.nan
            normal_comp = np.nan
            pi = np.nan

        rows.append({
            'week_key': prev_monday,
            'next_week': last_monday,
            'product_id': product_id,
            'product_name': product_name,
            'l1_category_name': l1,
            'pricing_bl_25': bl,
            'pareto_classification': pareto,
            'source_status': source_status,
            'price': base_price,
            'next_price': next_price,
            'cogs': cogs,
            'next_cogs': next_cogs,
            'comp_price': comp_price,
            'next_comp_price': next_comp_price,
            'normal_comp_price': normal_comp,
            'next_normal_comp_price': next_normal_comp,
            'pi': pi,
            'next_pi': next_pi_val,
        })

    df = pd.DataFrame(rows)
    return df


def dummy_pvm_bytes(seed=42):
    """Return PVM dummy data as xlsx bytes (for cached_pvm_compute compatibility)."""
    df = generate_pvm_dummy(seed=seed)
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    return buf.getvalue()


def dummy_pi_bytes(seed=42):
    """Return PI dummy data as xlsx bytes."""
    df = generate_pi_dummy(seed=seed)
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    return buf.getvalue()
