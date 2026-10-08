"""Synthetic CPG dataset with embedded storylines so investigations have real signal to find.

Storylines (relative to the latest week L):
  1. South region beverage stockouts ramp up over the last ~10 weeks.
  2. Salt & Co Chips national promo ran L-7..L-4 -> ended, with post-promo dip.
  3. Sparkle Detergent list price +9% from L-11 (Value segment is price sensitive).
  4. Competitor promo intensity spikes in Personal Care over the last 6 weeks.
  5. Crunch Bites West promo (L-17..L-14) cannibalised Crunch Minis.
  6. Planted data-quality problems: missing weeks, null discounts, stale inventory feed.
  7. Value-segment cohorts retain worse in recent months.
"""
from datetime import date, datetime, timedelta, timezone

import numpy as np
import pandas as pd
from sqlalchemy import inspect

from .db import engine

PRODUCTS = [
    # name, category, subcategory, brand, base weekly units (all cells), list price, unit cost
    ("Fizzo Cola", "Beverages", "Carbonated", "Fizzo", 9000, 1.80, 0.99),
    ("Fizzo Zero", "Beverages", "Carbonated", "Fizzo", 5500, 1.85, 0.96),
    ("Aqua Pure", "Beverages", "Water", "AquaPure", 7000, 0.90, 0.40),
    ("Citrus Cooler", "Beverages", "Juice", "Citrus", 3500, 2.40, 1.39),
    ("Crunch Bites", "Snacks", "Savoury", "Crunch", 4800, 2.20, 1.10),
    ("Crunch Minis", "Snacks", "Savoury", "Crunch", 3200, 1.60, 0.80),
    ("Salt & Co Chips", "Snacks", "Chips", "Salt & Co", 5200, 2.00, 0.96),
    ("Silk Shampoo", "Personal Care", "Hair", "Silk", 2600, 5.50, 2.20),
    ("Silk Conditioner", "Personal Care", "Hair", "Silk", 2000, 5.80, 2.32),
    ("Fresh Soap", "Personal Care", "Skin", "Fresh", 3000, 1.90, 0.80),
    ("Sparkle Detergent", "Household", "Laundry", "Sparkle", 2800, 8.50, 4.67),
    ("Sparkle Dish", "Household", "Dish", "Sparkle", 2400, 3.60, 1.87),
]
REGIONS = {"North": .22, "South": .24, "East": .20, "West": .19, "Central": .15}
CHANNELS = {"Supermarket": .45, "Convenience": .22, "E-commerce": .20, "Distributor": .13}
SEGMENTS = {"Premium": .25, "Standard": .50, "Value": .25}
AFFIN = {
    "Premium": {"Beverages": .9, "Snacks": .9, "Personal Care": 1.35, "Household": .9},
    "Standard": {"Beverages": 1, "Snacks": 1, "Personal Care": 1, "Household": 1},
    "Value": {"Beverages": 1.1, "Snacks": 1.1, "Personal Care": .65, "Household": 1.1},
}
SEG_ELAS = {"Premium": -.6, "Standard": -1.0, "Value": -1.5}
NW = 104


def needs_seed():
    return not inspect(engine()).has_table("fact_sales")


def build(force=False):
    if not force and not needs_seed():
        return False
    rng = np.random.default_rng(42)
    today = date.today()
    as_of = today - timedelta(days=today.weekday()) - timedelta(days=7)  # last fully completed week
    weeks = [as_of - timedelta(weeks=NW - 1 - i) for i in range(NW)]
    L = NW - 1
    names = [p[0] for p in PRODUCTS]
    pinfo = pd.DataFrame(PRODUCTS, columns=["product_name", "category", "subcategory", "brand", "base_units", "price", "cost"]).set_index("product_name")

    idx = pd.MultiIndex.from_product([range(NW), names, list(REGIONS), list(CHANNELS), list(SEGMENTS)],
                                     names=["wi", "product_name", "region", "channel", "segment"])
    df = idx.to_frame(index=False)
    for c in ["category", "subcategory", "brand"]:
        df[c] = df.product_name.map(pinfo[c])
    base = df.product_name.map(pinfo.base_units) * df.region.map(REGIONS) * df.channel.map(CHANNELS) * df.segment.map(SEGMENTS)
    base = base * np.array([AFFIN[s][c] for s, c in zip(df.segment, df.category)])
    woy = np.array([w.isocalendar()[1] for w in weeks])[df.wi.values]
    cat = df.category.values
    season = np.select(
        [cat == "Beverages", cat == "Snacks", cat == "Household"],
        [1 + .28 * np.sin(2 * np.pi * (woy - 14) / 52), 1 + .08 * np.sin(2 * np.pi * (woy - 40) / 52) + .10 * (woy >= 48), 1 + .05 * np.sin(2 * np.pi * (woy - 10) / 52)],
        default=1 + .03 * np.sin(2 * np.pi * (woy - 20) / 52))
    t = df.wi.values
    trend = 1.06 ** (t / 52)
    chan = np.where(df.channel == "E-commerce", 1.30 ** (t / 52), np.where(df.channel == "Supermarket", .99 ** (t / 52), 1.0))

    # list price
    lp = df.product_name.map(pinfo.price).values * np.where(t >= 52, 1.02, 1.0)
    lp = lp * np.where((df.product_name == "Sparkle Detergent") & (t >= L - 11), 1.09, 1.0)
    elas = df.segment.map(SEG_ELAS).values
    price_eff = (lp / (df.product_name.map(pinfo.price).values)) ** elas

    # promotions
    PROMOS = [
        ("PRM-001", "Crunch Bites", "West", None, L - 17, L - 14, .25, 1.8, "TPR", ["Crunch Minis"]),
        ("PRM-002", "Fizzo Cola", None, "Convenience", L - 30, L - 27, .15, 1.4, "Multi-buy", ["Fizzo Zero"]),
        ("PRM-003", "Salt & Co Chips", None, None, L - 7, L - 4, .20, 1.45, "TPR", []),
        ("PRM-004", "Crunch Bites", "West", None, L - 69, L - 66, .25, 1.7, "TPR", ["Crunch Minis"]),
        ("PRM-005", "Silk Shampoo", None, "Supermarket", L - 45, L - 42, .20, 1.5, "Feature", ["Silk Conditioner"]),
        ("PRM-006", "Citrus Cooler", "East", None, L - 23, L - 20, .18, 1.35, "TPR", []),
        ("PRM-007", "Fizzo Cola", "South", None, L - 62, L - 59, .20, 1.5, "TPR", ["Fizzo Zero"]),
    ]
    lift = np.ones(len(df)); disc = np.zeros(len(df)); promo = np.zeros(len(df), dtype=int)
    cann = np.ones(len(df)); post = np.ones(len(df))
    for pid, prod, reg, ch, s, e, d, lf, mech, sibs in PROMOS:
        scope = ((df.region == reg) if reg else True) & ((df.channel == ch) if ch else True)
        m = (df.product_name == prod) & scope & (t >= s) & (t <= e)
        lift = np.where(m, np.maximum(lift, lf), lift); disc = np.where(m, np.maximum(disc, d), disc); promo = np.where(m, 1, promo)
        if sibs:
            cann = np.where(df.product_name.isin(sibs) & scope & (t >= s) & (t <= e), cann * .82, cann)
        if pid in ("PRM-001", "PRM-003"):
            post = np.where((df.product_name == prod) & scope & (t > e) & (t <= e + 2), post * .88, post)

    # competitor effect on Personal Care (last 6 weeks)
    comp = np.where((df.category == "Personal Care") & (t >= L - 5), .94, 1.0)

    # inventory / stockouts at product x region x week
    inv = pd.MultiIndex.from_product([range(NW), names, list(REGIONS)], names=["wi", "product_name", "region"]).to_frame(index=False)
    inv["stockout_days"] = rng.choice([0, 1, 2], size=len(inv), p=[.97, .02, .01])
    ramp = {9: 0, 8: 1, 7: 1, 6: 1, 5: 2, 4: 2, 3: 5, 2: 5, 1: 5, 0: 5}
    for k, dd in ramp.items():
        m = (inv.region == "South") & inv.product_name.isin(["Fizzo Cola", "Fizzo Zero", "Aqua Pure", "Citrus Cooler"]) & (inv.wi == L - k)
        inv.loc[m, "stockout_days"] = np.maximum(inv.loc[m, "stockout_days"], dd)
    so = df.merge(inv, on=["wi", "product_name", "region"], how="left").stockout_days.values
    stock_f = 1 - .10 * so

    noise = rng.lognormal(0, .05, len(df))
    units = np.round(base * season * trend * chan * price_eff * lift * cann * post * comp * stock_f * noise).clip(lower=0).astype(int)
    gross = units * lp
    disc_eff = disc.copy()
    revenue = gross * (1 - disc_eff)
    cogs = units * df.product_name.map(pinfo.cost).values
    df["week_start"] = [weeks[i].isoformat() for i in df.wi]
    df["month"] = [weeks[i].strftime("%Y-%m") for i in df.wi]
    df["quarter"] = [f"{weeks[i].year}-Q{(weeks[i].month - 1) // 3 + 1}" for i in df.wi]
    df["year"] = [weeks[i].year for i in df.wi]
    df["units"] = units; df["list_price"] = lp.round(4); df["gross_revenue"] = gross.round(2)
    df["discount_pct"] = disc_eff; df["revenue"] = revenue.round(2); df["cogs"] = cogs.round(2); df["promo_flag"] = promo
    # planted data-quality issues
    miss = (df.product_name == "Aqua Pure") & (df.region == "East") & (df.channel == "E-commerce") & df.wi.isin([L - 20, L - 19])
    df = df[~miss].copy()
    ps = df[(df.product_name == "Salt & Co Chips") & (df.promo_flag == 1)].index
    df.loc[rng.choice(ps, 20, replace=False), "discount_pct"] = np.nan
    cols = ["week_start", "month", "quarter", "year", "product_name", "category", "subcategory", "brand", "region", "channel", "segment",
            "units", "list_price", "gross_revenue", "discount_pct", "revenue", "cogs", "promo_flag"]
    sales = df[cols]

    # inventory table
    up = df.groupby(["wi", "product_name", "region"]).units.sum().rename("u").reset_index()
    inv = inv.merge(up, on=["wi", "product_name", "region"], how="left").fillna({"u": 0})
    cover = np.clip(rng.normal(3.4, .5, len(inv)), .3, None) * np.where(inv.stockout_days > 0, np.maximum(.05, 1 - inv.stockout_days / 5), 1)
    inv["stock_on_hand"] = np.round(inv.u * cover).astype(int)
    inv["week_start"] = [weeks[i].isoformat() for i in inv.wi]
    inv["category"] = inv.product_name.map(pinfo.category); inv["brand"] = inv.product_name.map(pinfo.brand)
    inventory = inv[["week_start", "product_name", "category", "brand", "region", "stock_on_hand", "stockout_days"]]

    promos = pd.DataFrame([{
        "promo_id": pid, "product_name": prod, "category": pinfo.category[prod], "region": reg or "All", "channel": ch or "All",
        "start_week": weeks[s].isoformat(), "end_week": weeks[e].isoformat(), "discount_pct": d, "mechanic": mech,
        "siblings": ",".join(sibs)} for pid, prod, reg, ch, s, e, d, lf, mech, sibs in PROMOS])

    # competitor signals (external)
    rows = []
    for ct in ["Beverages", "Snacks", "Personal Care"]:
        for i, w in enumerate(weeks):
            pi_, pr = 1 + rng.normal(0, .015), np.clip(.30 + rng.normal(0, .05), .1, 1)
            if ct == "Personal Care" and i >= L - 5: pi_, pr = .93 + rng.normal(0, .01), .75 + rng.normal(0, .04)
            if ct == "Snacks" and L - 40 <= i <= L - 37: pr = .70 + rng.normal(0, .04)
            if ct == "Beverages" and L - 60 <= i <= L - 57: pr = .72 + rng.normal(0, .04)
            rows.append({"week_start": w.isoformat(), "category": ct, "price_index": round(pi_, 4), "promo_intensity": round(float(pr), 4), "source": "MarketScan (synthetic)"})
    competitor = pd.DataFrame(rows)

    # cohorts
    ay, am = as_of.year, as_of.month
    cohorts = []
    for k in range(17, -1, -1):
        tot = ay * 12 + am - 1 - k; cy, cm = tot // 12, tot % 12 + 1
        for sg, (kk, fl, sz) in {"Premium": (.12, .45, 1400), "Standard": (.18, .30, 2100), "Value": (.28, .15, 1800)}.items():
            if sg == "Value" and k <= 5: kk, fl = .40, .10
            size = int(rng.normal(sz, 120))
            for ms in range(0, k + 1):
                ret = fl + (1 - fl) * np.exp(-kk * ms)
                cohorts.append({"cohort_month": f"{cy}-{cm:02d}", "segment": sg, "months_since": ms, "cohort_size": size, "active_customers": int(size * ret * rng.normal(1, .015))})
    cohorts = pd.DataFrame(cohorts)

    nowu = datetime.now(timezone.utc)
    src = pd.DataFrame([
        ("Sales (POS + distributor)", "fact_sales", nowu - timedelta(hours=6), 24, "ERP / EDW", "Commercial Finance"),
        ("Inventory & availability", "fact_inventory", nowu - timedelta(hours=52), 24, "WMS", "Supply Chain"),
        ("Promotion calendar", "fact_promotions", nowu - timedelta(hours=6), 24, "Trade Promotion Mgmt", "Trade Marketing"),
        ("Competitor signals", "fact_competitor", nowu - timedelta(hours=30), 168, "External: MarketScan", "Strategy"),
        ("Customer cohorts", "fact_cohorts", nowu - timedelta(hours=6), 24, "CRM", "CRM"),
    ], columns=["source_name", "table_name", "last_refreshed", "cadence_hours", "system", "owner"])
    src["last_refreshed"] = src.last_refreshed.map(lambda d: d.isoformat(timespec="seconds"))

    eng = engine()
    for name, d in [("fact_sales", sales), ("fact_inventory", inventory), ("fact_promotions", promos), ("fact_competitor", competitor),
                    ("fact_cohorts", cohorts), ("data_sources", src)]:
        d.to_sql(name, eng, if_exists="replace", index=False, chunksize=5000)
    from .analytics import ops, core
    core.reset_caches()
    ops.run_dq_checks()
    return True
