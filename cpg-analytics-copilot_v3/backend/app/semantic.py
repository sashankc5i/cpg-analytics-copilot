"""Semantic layer: governed metrics, dimensions, hierarchies (DATA-004, GOV-004)."""
import numpy as np

from .analytics.errors import ToolError

SALES_DIMS = ["category", "brand", "product_name", "region", "channel", "segment"]
INV_DIMS = ["category", "brand", "product_name", "region"]
TIME_DIMS = ["week_start", "month", "quarter", "year"]
HIERARCHIES = {"product": ["category", "brand", "product_name"], "geography": ["region"], "channel": ["channel"], "customer": ["segment"]}
DIM_ALIASES = {"product": "product_name", "sku": "product_name", "products": "product_name", "regions": "region", "channels": "channel",
               "segments": "segment", "categories": "category", "brands": "brand", "customer_segment": "segment"}
SALES_BASE = ["revenue", "units", "cogs", "gross_revenue", "promo_revenue", "promo_units"]
INV_BASE = ["stockout_days", "pr_weeks", "stock_units"]


def _d(a, b):
    b = np.asarray(b, dtype=float)
    return np.where(b == 0, np.nan, np.asarray(a, dtype=float) / np.where(b == 0, 1, b))


METRICS = {
    "revenue": dict(name="Net Revenue", source="sales", unit="currency", additive=True, hib=True,
                    fn=lambda g: g("revenue"), desc="Net sales value after discounts, summed over the period.", formula="SUM(revenue)"),
    "units": dict(name="Units Sold", source="sales", unit="count", additive=True, hib=True,
                  fn=lambda g: g("units"), desc="Consumer units sold.", formula="SUM(units)"),
    "avg_price": dict(name="Average Net Price", source="sales", unit="price", additive=False, hib=True,
                      fn=lambda g: _d(g("revenue"), g("units")), desc="Net revenue per unit (after promotional discounts).", formula="SUM(revenue)/SUM(units)"),
    "gross_margin_pct": dict(name="Gross Margin %", source="sales", unit="pct", additive=False, hib=True,
                             fn=lambda g: _d(g("revenue") - g("cogs"), g("revenue")) * 100, desc="(Net revenue - COGS) / net revenue.", formula="(SUM(revenue)-SUM(cogs))/SUM(revenue)"),
    "promo_share": dict(name="Promo Share of Revenue", source="sales", unit="pct", additive=False, hib=None,
                        fn=lambda g: _d(g("promo_revenue"), g("revenue")) * 100, desc="Share of net revenue sold on promotion.", formula="SUM(revenue where promo_flag=1)/SUM(revenue)"),
    "discount_depth": dict(name="Average Discount Depth", source="sales", unit="pct", additive=False, hib=None,
                           fn=lambda g: (1 - _d(g("revenue"), g("gross_revenue"))) * 100, desc="Discount as a share of gross (list-price) revenue.", formula="1-SUM(revenue)/SUM(gross_revenue)"),
    "stockout_rate": dict(name="Stockout Rate", source="inventory", unit="pct", additive=False, hib=False,
                          fn=lambda g: _d(g("stockout_days"), 7 * g("pr_weeks")) * 100, desc="Stockout days as a share of product-region-days.", formula="SUM(stockout_days)/(7*COUNT(product-region-weeks))"),
    "stockout_days": dict(name="Stockout Days", source="inventory", unit="count", additive=True, hib=False,
                          fn=lambda g: g("stockout_days"), desc="Total product-region stockout days.", formula="SUM(stockout_days)"),
}
METRIC_STATUS = {}  # key -> status, refreshed from governance table


def metric(key):
    k = (key or "").strip().lower()
    alias = {"sales": "revenue", "net_revenue": "revenue", "volume": "units", "price": "avg_price", "margin": "gross_margin_pct"}
    k = alias.get(k, k)
    if k not in METRICS:
        raise ToolError(f"Unknown metric '{key}'. Approved metrics: {', '.join(METRICS)}.")
    if METRIC_STATUS.get(k) == "deprecated":
        raise ToolError(f"Metric '{k}' is deprecated in the governed metric catalog.")
    return {**METRICS[k], "key": k}


def norm_dim(d):
    d = (d or "").strip().lower()
    return DIM_ALIASES.get(d, d)


def mcalc(key, df, suf=""):
    return METRICS[key]["fn"](lambda c: df[c + suf].astype(float).values)
