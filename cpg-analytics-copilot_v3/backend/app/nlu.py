"""Lightweight deterministic NLU: entity/period/metric extraction used by the offline planner and investigation seeding."""
import re

from .analytics import core as C

SYN = {"channel": {"e-commerce": ["ecommerce", "e-commerce", "online"], "Supermarket": ["supermarket"], "Convenience": ["convenience"], "Distributor": ["distributor", "wholesale"]},
       "category": {"Beverages": ["beverage", "drinks"], "Snacks": ["snack"], "Personal Care": ["personal care"], "Household": ["household"]}}
MONTHS = {m: i + 1 for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}


def entities(text):
    t = text.lower(); out = {}
    vals = C.dim_values()
    for dim, vs in vals.items():
        hit = [v for v in vs if re.search(r"\b" + re.escape(v.lower()) + r"s?\b", t)]
        for canon, words in SYN.get(dim, {}).items():
            canon = next((v for v in vs if v.lower() == canon.lower()), canon)
            if canon in vs and any(w in t for w in words) and canon not in hit:
                hit.append(canon)
        if hit:
            out[dim] = sorted(set(hit))
    if "category" in out and "product_name" in out:  # a named product beats an incidental category word
        pass
    return out


def period(text):
    t = text.lower()
    m = re.search(r"last (\d+) weeks?", t)
    if m: return f"last_{m.group(1)}_weeks"
    m = re.search(r"\b(q[1-4])\s*(?:of\s*)?(\d{4})", t)
    if m: return f"{m.group(2)}-{m.group(1).upper()}"
    m = re.search(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s*(\d{4})", t)
    if m: return f"{m.group(2)}-{MONTHS[m.group(1)]:02d}"
    for k, v in [("last week", "last_1_weeks"), ("last month", "last_month"), ("last quarter", "last_quarter"), ("this month", "this_month"), ("this quarter", "this_quarter"), ("ytd", "ytd"), ("year to date", "ytd"), ("last year", "last_year")]:
        if k in t: return v
    return None


def compare_to(text):
    t = text.lower()
    if re.search(r"yoy|year over year|year-over-year|vs last year|prior year|last year", t): return "prior_year"
    return "prior_period"


def metric(text):
    t = text.lower()
    for k, v in [("margin", "gross_margin_pct"), ("promo share", "promo_share"), ("discount depth", "discount_depth"), ("stockout rate", "stockout_rate"), ("average price", "avg_price"), ("avg price", "avg_price"), ("units", "units"), ("volume", "units"), ("price", "avg_price")]:
        if k in t: return v
    return "revenue"


def group_by(text):
    t = text.lower()
    for k, v in [("product", "product_name"), ("sku", "product_name"), ("categor", "category"), ("region", "region"), ("channel", "channel"), ("segment", "segment"), ("brand", "brand")]:
        if re.search(r"\b(by|per|across|each|top \d+|bottom \d+|which)\b[^.?]*" + k, t) or re.search(r"\b" + k + r"(s|ies)?\b.*\b(performance|ranking)", t):
            return [v]
    return []


def parse(text):
    n = re.search(r"\b(?:top|bottom|best|worst)\s+(\d+)", text.lower())
    return {"metric": metric(text), "period": period(text), "compare_to": compare_to(text), "filters": entities(text), "group_by": group_by(text),
            "n": int(n.group(1)) if n else 5, "order": "bottom" if re.search(r"bottom|worst|lowest|weakest", text.lower()) else "top"}
