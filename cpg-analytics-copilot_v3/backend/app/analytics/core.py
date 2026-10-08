"""Deterministic analytics core: periods, governed SQL builder, row-level scope, comparison frames."""
import re
from datetime import date, timedelta

import numpy as np
import pandas as pd

from .. import semantic as S
from ..config import settings
from ..db import fetch_df
from .errors import PolicyError, ToolError

SALES_SQL = ("SUM(revenue) AS revenue, SUM(units) AS units, SUM(cogs) AS cogs, SUM(gross_revenue) AS gross_revenue, "
             "SUM(CASE WHEN promo_flag = 1 THEN revenue ELSE 0 END) AS promo_revenue, "
             "SUM(CASE WHEN promo_flag = 1 THEN units ELSE 0 END) AS promo_units, COUNT(DISTINCT week_start) AS n_weeks")
INV_SQL = "SUM(stockout_days) AS stockout_days, COUNT(*) AS pr_weeks, SUM(stock_on_hand) AS stock_units, COUNT(DISTINCT week_start) AS n_weeks"
TABLES = {"sales": "fact_sales", "inventory": "fact_inventory"}

_cache = {}
W7 = timedelta(days=7)


def reset_caches():
    _cache.clear()


class Ctx:
    """Per-request execution context carrying row-level scope + lineage trace."""

    def __init__(self, scope=None, user=None, request_id="-"):
        self.scope = scope or {}
        self.user = user
        self.request_id = request_id
        self.sqls, self.tables, self.warnings, self.periods = [], set(), [], []
        self.filters = {}
        self.scoped = False

    def warn(self, m):
        if m not in self.warnings:
            self.warnings.append(m)


# ---------------- reference data ----------------
def as_of():
    if "asof" not in _cache:
        _cache["asof"] = date.fromisoformat(str(fetch_df("SELECT MAX(week_start) AS m FROM fact_sales").iloc[0, 0])[:10])
    return _cache["asof"]


def data_min():
    if "dmin" not in _cache:
        _cache["dmin"] = date.fromisoformat(str(fetch_df("SELECT MIN(week_start) AS m FROM fact_sales").iloc[0, 0])[:10])
    return _cache["dmin"]


def dim_values():
    if "dims" not in _cache:
        d = {}
        for c in S.SALES_DIMS:
            d[c] = sorted(fetch_df(f"SELECT DISTINCT {c} AS v FROM fact_sales").v.dropna().tolist())
        _cache["dims"] = d
    return _cache["dims"]


def product_map():
    if "pmap" not in _cache:
        df = fetch_df("SELECT DISTINCT product_name, category, brand, subcategory FROM fact_sales")
        _cache["pmap"] = {r.product_name: dict(category=r.category, brand=r.brand, subcategory=r.subcategory) for r in df.itertuples()}
    return _cache["pmap"]


# ---------------- periods ----------------
class Period:
    def __init__(self, start, end, label, kind):
        self.start, self.end, self.label, self.kind = start, end, label, kind

    @property
    def weeks(self):
        first = self.start + timedelta(days=(7 - self.start.weekday()) % 7)
        return 0 if first > self.end else (self.end - first).days // 7 + 1

    def to_dict(self):
        return {"start": self.start.isoformat(), "end": self.end.isoformat(), "label": self.label, "kind": self.kind, "weeks": self.weeks}


def _mb(y, m):
    nxt = date(y + (m == 12), m % 12 + 1, 1)
    return date(y, m, 1), nxt - timedelta(days=1)


def _am(y, m, k):
    t = y * 12 + m - 1 + k
    return t // 12, t % 12 + 1


def _q(y, q):
    return date(y, 3 * q - 2, 1), _mb(y, 3 * q)[1]


def resolve_period(spec=None):
    ao = as_of()
    ref = ao + timedelta(days=6)  # latest data day; calendar words are relative to it
    raw = str(spec or "last_12_weeks").strip().lower()
    w = raw.replace(" ", "_")
    P = lambda s, e, lab, k: Period(max(s, data_min()), min(e, ao), lab, k)
    m = re.fullmatch(r"last_(\d+)_weeks?", w)
    if m:
        n = int(m.group(1)); return P(ao - timedelta(weeks=n - 1), ao, f"last {n} weeks", "weeks")
    if w == "last_week":
        return P(ao, ao, "last week", "weeks")
    m = re.fullmatch(r"last_(\d+)_months?", w)
    if m:
        n = int(m.group(1)); y, mo = _am(ref.year, ref.month, -1); sy, sm = _am(y, mo, -(n - 1))
        return P(date(sy, sm, 1), _mb(y, mo)[1], f"last {n} months", "range")
    if w == "last_month":
        y, mo = _am(ref.year, ref.month, -1); s, e = _mb(y, mo); return P(s, e, s.strftime("%b %Y"), "month")
    if w in ("this_month", "mtd", "month_to_date"):
        s, _ = _mb(ref.year, ref.month); return P(s, ao, s.strftime("%b %Y") + " (to date)", "range")
    if w in ("last_quarter", "this_quarter"):
        q = (ref.month - 1) // 3 + 1
        if w == "last_quarter":
            q -= 1
            y = ref.year
            if q == 0: q, y = 4, y - 1
            s, e = _q(y, q); return P(s, e, f"{y}-Q{q}", "quarter")
        s, e = _q(ref.year, q); return P(s, ao, f"{ref.year}-Q{q} (to date)", "range")
    if w in ("ytd", "year_to_date"):
        return P(date(ref.year, 1, 1), ao, f"{ref.year} YTD", "ytd")
    if w == "last_year":
        return P(date(ref.year - 1, 1, 1), date(ref.year - 1, 12, 31), str(ref.year - 1), "year")
    if w in ("all", "all_time"):
        return Period(data_min(), ao, "all data", "range")
    if re.fullmatch(r"\d{4}-\d{2}", raw):
        y, mo = int(raw[:4]), int(raw[5:]); s, e = _mb(y, mo); return P(s, e, s.strftime("%b %Y"), "month")
    m = re.fullmatch(r"(\d{4})-?q([1-4])", raw)
    if m:
        y, q = int(m.group(1)), int(m.group(2)); s, e = _q(y, q); return P(s, e, f"{y}-Q{q}", "quarter")
    if re.fullmatch(r"\d{4}", raw):
        y = int(raw); return P(date(y, 1, 1), date(y, 12, 31), raw, "year")
    m = re.fullmatch(r"(\d{4}-\d{2}-\d{2})\.\.(\d{4}-\d{2}-\d{2})", raw)
    if m:
        return P(date.fromisoformat(m.group(1)), date.fromisoformat(m.group(2)), raw, "range")
    raise ToolError(f"Unsupported period '{spec}'. Use e.g. last_4_weeks, last_12_weeks, last_month, last_quarter, ytd, 2026-08, 2026-Q2 or YYYY-MM-DD..YYYY-MM-DD.")


def shift(p, how):
    how = (how or "prior_period").lower()
    if how in ("none", ""):
        return None
    how = {"mom": "prior_period" if p.kind == "month" else "prior_period", "qoq": "prior_period", "yoy": "prior_year", "py": "prior_year"}.get(how, how)
    if how == "prior_year":
        if p.kind == "month":
            y, mo = _am(p.start.year, p.start.month, -12); s, e = _mb(y, mo); return Period(s, e, s.strftime("%b %Y"), "month")
        if p.kind == "quarter":
            y, q = p.start.year - 1, (p.start.month - 1) // 3 + 1; s, e = _q(y, q); return Period(s, e, f"{y}-Q{q}", "quarter")
        if p.kind in ("year", "ytd"):
            return Period(date(p.start.year - 1, p.start.month, p.start.day), p.end - timedelta(days=364), f"{p.label} (prior year)", "range")
        return Period(p.start - timedelta(days=364), p.end - timedelta(days=364), f"{p.label} (prior year)", "range")
    if how != "prior_period":
        raise ToolError("compare_to must be one of prior_period, prior_year, mom, qoq, yoy, none.")
    if p.kind == "month":
        y, mo = _am(p.start.year, p.start.month, -1); s, e = _mb(y, mo); return Period(s, e, s.strftime("%b %Y"), "month")
    if p.kind == "quarter":
        y, q = p.start.year, (p.start.month - 1) // 3 + 1 - 1
        if q == 0: q, y = 4, y - 1
        s, e = _q(y, q); return Period(s, e, f"{y}-Q{q}", "quarter")
    if p.kind in ("year", "ytd"):
        return shift(p, "prior_year")
    if p.kind == "weeks":  # end is the start date of the final week
        return Period(p.start - timedelta(weeks=p.weeks), p.start - W7, f"prior {p.label}", "weeks")
    n = (p.end - p.start).days + 1
    return Period(p.start - timedelta(days=n), p.start - timedelta(days=1), f"prior {p.label}", "range")


# ---------------- filters, scope, SQL ----------------
def norm_filters(filters):
    out = {}
    vals = dim_values()
    for k, v in (filters or {}).items():
        dim = S.norm_dim(k)
        if dim not in S.SALES_DIMS:
            raise ToolError(f"Unknown filter dimension '{k}'. Valid: {', '.join(S.SALES_DIMS)}.")
        items = v if isinstance(v, list) else [v]
        keep = []
        for it in items:
            s = str(it).strip().lower()
            hit = [x for x in vals[dim] if x.lower() == s] or [x for x in vals[dim] if s in x.lower() or x.lower() in s]
            if len(hit) != 1:
                raise ToolError(f"Value '{it}' not recognised for {dim}. Valid values: {', '.join(vals[dim])}.")
            keep.append(hit[0])
        if keep:
            out[dim] = sorted(set(keep))
    return out


def apply_scope(ctx, source, filters):
    f = {k: list(v) for k, v in (filters or {}).items()}
    for dim, allowed in ctx.scope.items():
        if source == "inventory" and dim not in S.INV_DIMS:
            raise PolicyError(f"Inventory data cannot be restricted by {dim}; it is unavailable under your data-access policy.")
        if dim in f:
            keep = [v for v in f[dim] if v in allowed]
            if not keep:
                raise PolicyError(f"Your data-access policy does not include {dim} = {', '.join(f[dim])}.")
            f[dim] = keep
        else:
            f[dim] = list(allowed)
        ctx.scoped = True
    ctx.filters = f
    return f


def fetch(ctx, source, group_by, filters, start, end, extra_where=""):
    dims = S.SALES_DIMS if source == "sales" else S.INV_DIMS
    allowed = dims + S.TIME_DIMS
    group_by = [S.norm_dim(g) for g in (group_by or [])]
    for g in group_by:
        if g not in allowed:
            raise ToolError(f"'{g}' cannot be used for {source} metrics. Valid: {', '.join(allowed)}.")
    f = apply_scope(ctx, source, filters)
    where = ["week_start BETWEEN :start AND :end"]
    params = {"start": start.isoformat(), "end": end.isoformat()}
    exp = []
    for k, v in f.items():
        if k not in dims:
            raise ToolError(f"Filter '{k}' is not available for {source} metrics.")
        where.append(f"{k} IN :f_{k}")
        params["f_" + k] = v
        exp.append("f_" + k)
    if extra_where:
        where.append(extra_where)
    sel = ", ".join(group_by)
    sql = (f"SELECT {sel + ', ' if sel else ''}{SALES_SQL if source == 'sales' else INV_SQL} FROM {TABLES[source]} "
           f"WHERE {' AND '.join(where)}{' GROUP BY ' + sel if sel else ''}")
    df = fetch_df(sql, params, exp)
    ctx.sqls.append({"sql": sql, "params": params})
    ctx.tables.add(TABLES[source])
    base = S.SALES_BASE if source == "sales" else S.INV_BASE
    for b in base:
        if b in df:
            df[b] = df[b].fillna(0).astype(float)
    return df


def compare_frames(ctx, source, group_by, filters, cur, prior):
    """prior may be None, a Period, or a list of Periods (averaged: trailing benchmark)."""
    base = S.SALES_BASE if source == "sales" else S.INV_BASE
    ctx.periods.append(cur)
    c = fetch(ctx, source, group_by, filters, cur.start, cur.end)
    priors = prior if isinstance(prior, list) else ([prior] if prior is not None else [])
    ps = []
    for pr in priors:
        ctx.periods.append(pr)
        pf = fetch(ctx, source, group_by, filters, pr.start, pr.end)
        wc, wp = cur.weeks, pr.weeks
        if wp and wc and wc != wp:
            for b in base:
                pf[b] = pf[b] * (wc / wp)
            ctx.warn(f"Comparison period has {wp} weeks vs {wc} in the current period; comparison values were scaled to {wc} weeks for a like-for-like comparison.")
        if pr.start < data_min():
            ctx.warn("The comparison period starts before the available history; comparison values may be incomplete.")
        ps.append(pf)
    if ps:
        allp = pd.concat(ps)
        p = (allp.groupby(group_by)[base].sum().reset_index() if group_by else allp[base].sum().to_frame().T) 
        p[base] = p[base] / len(ps)
    else:
        p = c.iloc[0:0].copy()
    keep = lambda d, sfx: d[[*group_by, *base]].rename(columns={b: b + sfx for b in base})
    if group_by:
        m = keep(c, "_c").merge(keep(p, "_p"), on=group_by, how="outer")
    else:
        m = pd.concat([keep(c, "_c").reset_index(drop=True), keep(p, "_p").reset_index(drop=True)], axis=1)
        if len(m) == 0:
            m = pd.DataFrame([{}])
    for b in base:
        for sfx in ("_c", "_p"):
            if b + sfx not in m:
                m[b + sfx] = 0.0
            m[b + sfx] = m[b + sfx].fillna(0.0)
    return m


def totals(m, source):
    base = S.SALES_BASE if source == "sales" else S.INV_BASE
    return pd.DataFrame([{b + s: m[b + s].sum() for b in base for s in ("_c", "_p")}])


def compare_table(ctx, metric_key, group_by, filters, cur, prior):
    """Returns (table, totals dict). Table has cur/prior/delta/pct/share and (for additive metrics) contribution columns."""
    m = S.metric(metric_key)
    mf = compare_frames(ctx, m["source"], group_by, filters, cur, prior)
    t = totals(mf, m["source"])
    mf["cur"] = S.mcalc(metric_key, mf, "_c")
    mf["prior"] = S.mcalc(metric_key, mf, "_p")
    tc, tp = float(S.mcalc(metric_key, t, "_c")[0]), float(S.mcalc(metric_key, t, "_p")[0])
    mf["delta"] = mf.cur - mf.prior
    mf["pct"] = np.where(mf.prior.abs() > 1e-9, mf.delta / mf.prior.abs() * 100, np.nan)
    tdelta = tc - tp
    if m["additive"]:
        mf["share_cur"] = np.where(abs(tc) > 1e-9, mf.cur / tc * 100, np.nan)
        mf["share_gap"] = np.where(abs(tdelta) > 1e-9, mf.delta / tdelta * 100, np.nan)
    tot = {"cur": tc, "prior": tp, "delta": tdelta, "pct": (tdelta / abs(tp) * 100) if abs(tp) > 1e-9 else None}
    return mf, tot


# ---------------- formatting ----------------
def money(v, sign=False):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "n/a"
    s = settings.currency
    a = abs(v)
    t = f"{a / 1e6:.2f}M" if a >= 1e6 else f"{a / 1e3:.1f}K" if a >= 1e3 else f"{a:.2f}" if a < 10 else f"{a:.0f}"
    pre = ("-" if v < 0 else "+" if sign else "")
    return f"{pre}{s}{t}"


def fnum(v, sign=False):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "n/a"
    a = abs(v)
    t = f"{a / 1e6:.2f}M" if a >= 1e6 else f"{a / 1e3:.1f}K" if a >= 1e4 else f"{a:,.0f}"
    return ("-" if v < 0 else "+" if sign else "") + t


def fmt(metric_key, v, sign=False):
    u = S.METRICS[metric_key]["unit"]
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "n/a"
    if u == "currency": return money(v, sign)
    if u == "pct": return f"{'+' if sign and v > 0 else ''}{v:.1f}%"
    if u == "price": return f"{settings.currency}{v:.2f}"
    return fnum(v, sign)


def pct(v, sign=True):
    return "n/a" if v is None or (isinstance(v, float) and np.isnan(v)) else f"{'+' if sign and v > 0 else ''}{v:.1f}%"


def clean(v, nd=2):
    if isinstance(v, (float, np.floating)):
        return None if np.isnan(v) or np.isinf(v) else round(float(v), nd)
    if isinstance(v, (np.integer,)):
        return int(v)
    return v


def rows(df, cols=None, nd=2):
    cols = cols or list(df.columns)
    return [{c: clean(r[c], nd) for c in cols} for _, r in df.iterrows()]


# ---------------- result + chart builders ----------------
def result(headline, rows_=None, chart=None, facts=None, limits=None, columns=None):
    return {"headline": headline, "rows": rows_ or [], "columns": columns, "chart": chart, "facts": facts or {}, "limitations": limits or []}


def chart_bar(title, data, series, unit="count", x="name", signed=False):
    return {"type": "bar", "title": title, "unit": unit, "x": x, "series": series, "data": data, "signed": signed}


def chart_line(title, data, series, unit="count", x="name", band=None, split=None):
    return {"type": "line", "title": title, "unit": unit, "x": x, "series": series, "data": data, "band": band, "split": split}


def chart_waterfall(title, steps, unit="currency"):
    data, run = [], 0.0
    for s in steps:
        v = float(s["value"])
        if s.get("total"):
            data.append({"name": s["name"], "base": 0, "up": max(v, 0), "down": 0, "total": v, "kind": "total"}); run = v
        else:
            lo, hi = (run, run + v) if v >= 0 else (run + v, run)
            data.append({"name": s["name"], "base": min(lo, hi) if lo >= 0 else lo, "up": v if v >= 0 else 0, "down": -v if v < 0 else 0, "delta": v, "kind": "delta"}); run += v
    return {"type": "waterfall", "title": title, "unit": unit, "x": "name", "data": data}


def label_of(row, group_by):
    return " / ".join(str(row[g]) for g in group_by) if group_by else "Total"


def onset(series, direction, baseline_n=8, k=1.0, consec=2):
    """First index (position) where series deviates from its leading baseline by >k sigma for `consec` weeks."""
    s = np.asarray(series, dtype=float)
    if len(s) < baseline_n + consec + 1:
        return None
    base = s[:baseline_n]
    mu, sd = base.mean(), max(base.std(ddof=1), 1e-9, abs(base.mean()) * 0.01)
    flag = ((s - mu) / sd * (1 if direction > 0 else -1)) > k
    for i in range(baseline_n, len(s) - consec + 1):
        if flag[i:i + consec].all():
            return i
    return None
