"""Core analytical tools (DATA-001..010, INV-007/008, CPG-001/002/003/005/006/012/013/014, PBI-007)."""
import numpy as np
import pandas as pd

from .. import semantic as S
from . import core as C
from .errors import ToolError


def _gb(group_by, maxn=3):
    gb = [S.norm_dim(g) for g in (group_by or [])]
    if len(gb) > maxn:
        raise ToolError(f"Group by at most {maxn} dimensions.")
    return gb


def _period_pair(period, compare_to, default="last_4_weeks"):
    cur = C.resolve_period(period or default)
    return cur, C.shift(cur, compare_to)


def _total_value(metric, df, source):
    base = S.SALES_BASE if source == "sales" else S.INV_BASE
    return float(S.mcalc(metric, pd.DataFrame([df[base].sum()]))[0])


# ---------------------------------------------------------------- query / top-bottom
def query_metric(ctx, metric, group_by=None, filters=None, period=None, limit=20):
    m = S.metric(metric); cur = C.resolve_period(period or "last_4_weeks"); f = C.norm_filters(filters); gb = _gb(group_by)
    ctx.periods.append(cur)
    df = C.fetch(ctx, m["source"], gb, f, cur.start, cur.end)
    tot = _total_value(metric, df, m["source"])
    if gb:
        df["value"] = S.mcalc(metric, df)
        df = df.sort_values("value", ascending=False)
        if m["additive"] and abs(tot) > 0:
            df["share"] = df.value / tot * 100
        out = C.rows(df.head(int(limit)), [*gb, "value"] + (["share"] if "share" in df else []))
        top = df.iloc[0]
        head = f"{m['name']} for {cur.label}: {C.fmt(metric, tot)} total; highest {C.label_of(top, gb)} at {C.fmt(metric, top.value)}."
        ch = C.chart_bar(f"{m['name']} by {', '.join(gb)} — {cur.label}", [{"name": C.label_of(r, gb), "value": C.clean(r.value)} for _, r in df.head(int(limit)).iterrows()],
                         [{"key": "value", "name": m["name"]}], m["unit"])
    else:
        out = [{"metric": m["name"], "value": C.clean(tot), "period": cur.label}]
        head = f"{m['name']} for {cur.label}: {C.fmt(metric, tot)}."
        ch = None
    return C.result(head, out, ch, {"total": C.clean(tot), "period": cur.to_dict()})


def top_bottom(ctx, metric, group_by, n=5, order="top", period=None, filters=None):
    m = S.metric(metric); n = max(1, min(int(n), 25)); gb = _gb(group_by, 2)
    if not gb:
        raise ToolError("group_by is required for top/bottom analysis.")
    cur = C.resolve_period(period or "last_4_weeks"); f = C.norm_filters(filters); ctx.periods.append(cur)
    df = C.fetch(ctx, m["source"], gb, f, cur.start, cur.end)
    tot = _total_value(metric, df, m["source"])
    df["value"] = S.mcalc(metric, df)
    df = df.dropna(subset=["value"]).sort_values("value", ascending=(order == "bottom")).head(n)
    df["rank"] = range(1, len(df) + 1)
    if m["additive"] and tot:
        df["share"] = df.value / tot * 100
    names = [f"{C.label_of(r, gb)} ({C.fmt(metric, r.value)})" for _, r in df.head(3).iterrows()]
    head = f"{'Top' if order != 'bottom' else 'Bottom'} {len(df)} {gb[-1]} by {m['name']} ({cur.label}): " + "; ".join(names) + ("…" if len(df) > 3 else "") + "."
    ch = C.chart_bar(head.split(":")[0], [{"name": C.label_of(r, gb), "value": C.clean(r.value)} for _, r in df.iterrows()], [{"key": "value", "name": m["name"]}], m["unit"])
    return C.result(head, C.rows(df, ["rank", *gb, "value"] + (["share"] if "share" in df else [])), ch,
                    {"total": C.clean(tot), "leader": C.label_of(df.iloc[0], gb), "period": cur.to_dict()},
                    ["Results are bounded to at most 25 rows."])


# ---------------------------------------------------------------- compare / variance
def compare_periods(ctx, metric, period=None, compare_to="prior_period", group_by=None, filters=None, limit=10, order_by="abs_delta"):
    m = S.metric(metric); gb = _gb(group_by); cur, prior = _period_pair(period, compare_to); f = C.norm_filters(filters)
    mf, tot = C.compare_table(ctx, metric, gb, f, cur, prior)
    nm = m["name"]
    if prior is None:
        raise ToolError("compare_to cannot be 'none' for compare_periods. Use query_metric for a single period.")
    head = f"{nm} {cur.label} vs {prior.label}: {C.fmt(metric, tot['cur'])} vs {C.fmt(metric, tot['prior'])} ({C.pct(tot['pct'])}, {C.fmt(metric, tot['delta'], True)})."
    if gb:
        mf = mf.reindex(mf.delta.abs().sort_values(ascending=False).index) if order_by == "abs_delta" else mf.sort_values("cur", ascending=False)
        top = mf.head(int(limit))
        cols = [*gb, "cur", "prior", "delta", "pct"] + (["share_cur", "share_gap"] if m["additive"] else [])
        r0 = mf.iloc[0]
        head += f" Largest mover: {C.label_of(r0, gb)} ({C.fmt(metric, r0.delta, True)}, {C.pct(r0.pct)})."
        data = [{"name": C.label_of(r, gb), "current": C.clean(r.cur), "prior": C.clean(r.prior), "delta": C.clean(r.delta)} for _, r in top.iterrows()]
        ch = C.chart_bar(f"{nm}: {cur.label} vs {prior.label} by {', '.join(gb)}", data,
                         [{"key": "prior", "name": prior.label}, {"key": "current", "name": cur.label}], m["unit"])
        out = C.rows(top, cols)
    else:
        data = [{"name": prior.label, "value": C.clean(tot["prior"])}, {"name": cur.label, "value": C.clean(tot["cur"])}]
        ch = C.chart_bar(f"{nm}: {cur.label} vs {prior.label}", data, [{"key": "value", "name": nm}], m["unit"])
        out = [{"current": C.clean(tot["cur"]), "prior": C.clean(tot["prior"]), "delta": C.clean(tot["delta"]), "pct": C.clean(tot["pct"])}]
    return C.result(head, out, ch, {"current": C.clean(tot["cur"]), "prior": C.clean(tot["prior"]), "delta": C.clean(tot["delta"]), "pct": C.clean(tot["pct"]),
                                   "current_period": cur.to_dict(), "prior_period": prior.to_dict()})


def variance_analysis(ctx, metric, period=None, benchmark="prior_period", dimension=None, filters=None, limit=6):
    m = S.metric(metric); cur = C.resolve_period(period or "last_4_weeks"); f = C.norm_filters(filters)
    if benchmark == "trailing_avg":
        ps = [C.shift(cur, "prior_period")]
        for _ in range(3):
            ps.append(C.shift(ps[-1], "prior_period"))
        prior, blabel = ps, "trailing 4-period average"
    else:
        prior = C.shift(cur, benchmark if benchmark in ("prior_period", "prior_year") else "prior_period"); blabel = prior.label
    dims = [S.norm_dim(dimension)] if dimension else (["region", "channel", "category", "segment", "product_name"] if m["source"] == "sales" else ["region", "category", "product_name"])
    mf0, tot = C.compare_table(ctx, metric, [], f, cur, prior)
    head = f"{m['name']} variance vs {blabel}: {C.fmt(metric, tot['delta'], True)} ({C.pct(tot['pct'])}); actual {C.fmt(metric, tot['cur'])} vs benchmark {C.fmt(metric, tot['prior'])}."
    if not m["additive"]:
        return C.result(head, [{"actual": C.clean(tot["cur"]), "benchmark": C.clean(tot["prior"]), "variance": C.clean(tot["delta"])}], None, {"variance": C.clean(tot["delta"])},
                        ["Contributor decomposition is only available for additive metrics (revenue, units, stockout_days)."])
    contrib, best = [], None
    for d in dims:
        mf, _ = C.compare_table(ctx, metric, [d], f, cur, prior)
        mf = mf.reindex(mf.delta.abs().sort_values(ascending=False).index)
        for _, r in mf.head(3).iterrows():
            contrib.append({"dimension": d, "member": r[d], "variance": C.clean(r.delta), "share_of_variance": C.clean(r.share_gap), "pct_vs_benchmark": C.clean(r.pct)})
        top_share = abs(mf.iloc[0].share_gap) if len(mf) and pd.notna(mf.iloc[0].share_gap) else 0
        if best is None or top_share > best[0]:
            best = (top_share, d, mf)
    _, bd, bmf = best
    steps = [{"name": "Benchmark", "value": tot["prior"], "total": True}]
    shown = bmf.head(int(limit))
    steps += [{"name": str(r[bd]), "value": r.delta} for _, r in shown.iterrows()]
    other = tot["delta"] - shown.delta.sum()
    if abs(other) > 1e-9 and len(bmf) > len(shown):
        steps.append({"name": "Other", "value": other})
    steps.append({"name": "Actual", "value": tot["cur"], "total": True})
    contrib.sort(key=lambda r: -abs(r["variance"] or 0))
    lead = contrib[0]
    head += f" Largest contributor: {lead['member']} ({lead['dimension']}) at {C.fmt(metric, lead['variance'], True)}, {C.clean(lead['share_of_variance'], 0)}% of the variance."
    return C.result(head, contrib[:12], C.chart_waterfall(f"{m['name']} variance bridge by {bd}", steps, m["unit"]),
                    {"variance": C.clean(tot["delta"]), "pct": C.clean(tot["pct"]), "benchmark": blabel, "best_dimension": bd, "contributors": contrib[:8]})


# ---------------------------------------------------------------- trend
def trend_analysis(ctx, metric, grain="week", period="last_26_weeks", filters=None, group_by=None):
    m = S.metric(metric); col = {"week": "week_start", "month": "month", "quarter": "quarter"}.get(grain)
    if not col:
        raise ToolError("grain must be week, month or quarter.")
    cur = C.resolve_period(period or "last_26_weeks"); f = C.norm_filters(filters); gb = _gb(group_by, 1); ctx.periods.append(cur)
    df = C.fetch(ctx, m["source"], [col, *gb], f, cur.start, cur.end)
    df["value"] = S.mcalc(metric, df)
    per_week = m["additive"] and grain != "week"
    if per_week:
        df["value"] = df.value / df.n_weeks.clip(lower=1)
    df = df.sort_values(col)
    unit_note = " (weekly average)" if per_week else ""
    groups = [None] if not gb else df.groupby(gb[0]).value.sum().sort_values(ascending=False).head(6).index.tolist()
    summaries, rows_ = [], []
    for g in groups:
        s = df if g is None else df[df[gb[0]] == g]
        v = s.value.values
        if len(v) < 3:
            continue
        x = np.arange(len(v)); slope = np.polyfit(x, v, 1)[0]; mean = np.nanmean(v)
        total_change = slope * (len(v) - 1) / mean * 100 if mean else 0
        chg = np.diff(v) / np.where(v[:-1] == 0, np.nan, v[:-1]) * 100
        thr = 2 * np.nanstd(chg) if np.isfinite(chg).sum() > 3 else np.inf
        mats = [(s[col].iloc[i + 1], float(chg[i])) for i in range(len(chg)) if np.isfinite(chg[i]) and abs(chg[i]) > max(thr, 3)]
        direction = "up" if total_change > 3 else "down" if total_change < -3 else "flat"
        summaries.append({"group": g or "Total", "direction": direction, "fitted_change_pct": C.clean(total_change), "first": C.clean(v[0]), "last": C.clean(v[-1]),
                          "peak": C.clean(np.nanmax(v)), "trough": C.clean(np.nanmin(v)), "material_moves": [{"bucket": a, "change_pct": C.clean(b)} for a, b in mats[:5]]})
    if not summaries:
        raise ToolError("Not enough history in this period for a trend (need at least 3 points).")
    wide = df.pivot_table(index=col, columns=gb[0], values="value", aggfunc="sum").reset_index() if gb else df[[col, "value"]].copy()
    wide = wide.rename(columns={col: "name"})
    series = [{"key": str(c), "name": str(c)} for c in wide.columns if c != "name"]
    if gb:
        series = [s_ for s_ in series if s_["key"] in [str(g) for g in groups]]
    data = [{k: (C.clean(v) if k != "name" else str(v)) for k, v in r.items()} for r in wide.to_dict("records")]
    main = summaries[0]
    head = f"{m['name']}{unit_note} {cur.label}: trending {main['direction']} ({C.pct(main['fitted_change_pct'])} fitted change), from {C.fmt(metric, main['first'])} to {C.fmt(metric, main['last'])}."
    if main["material_moves"]:
        mv = main["material_moves"][0]; head += f" Largest single move: {mv['bucket']} ({C.pct(mv['change_pct'])})."
    return C.result(head, summaries if gb else data, C.chart_line(f"{m['name']}{unit_note} by {grain}", data, series, m["unit"]),
                    {"summaries": summaries, "grain": grain, "period": cur.to_dict()},
                    ["Monthly/quarterly buckets are shown as weekly averages so 4- and 5-week months are comparable."] if per_week else [])


# ---------------------------------------------------------------- drill-down
def drilldown(ctx, metric, hierarchy="product", period=None, compare_to="prior_period", filters=None, level=None):
    m = S.metric(metric); hier = S.HIERARCHIES.get(S.norm_dim(hierarchy) if hierarchy not in S.HIERARCHIES else hierarchy)
    if not hier:
        raise ToolError(f"hierarchy must be one of {', '.join(S.HIERARCHIES)}.")
    f = C.norm_filters(filters); cur, prior = _period_pair(period, compare_to)
    path, nxt = [], None
    for lv in hier:
        if len(f.get(lv, [])) == 1:
            path.append({"level": lv, "member": f[lv][0]})
        else:
            nxt = lv; break
    nxt = nxt or hier[-1]
    if level:
        lv = S.norm_dim(level)
        if lv not in hier:
            raise ToolError(f"level must be one of {hier} for the {hierarchy} hierarchy.")
        nxt = lv
    mf, tot = C.compare_table(ctx, metric, [nxt], f, cur, prior)
    mf = mf.sort_values("cur", ascending=False)
    cols = [nxt, "cur", "prior", "delta", "pct"] + (["share_cur"] if m["additive"] else [])
    crumb = " > ".join(["Company"] + [p["member"] for p in path])
    top = mf.iloc[0]
    head = f"{m['name']} at {crumb} for {cur.label}: {C.fmt(metric, tot['cur'])}" + (f" ({C.pct(tot['pct'])} vs {prior.label})" if prior else "") + f". Breakdown by {nxt}: largest is {top[nxt]} ({C.fmt(metric, top.cur)})."
    data = [{"name": str(r[nxt]), "current": C.clean(r.cur), "prior": C.clean(r.prior), "delta": C.clean(r.delta)} for _, r in mf.iterrows()]
    ch = C.chart_bar(f"{m['name']} by {nxt} ({crumb})", data, [{"key": "prior", "name": prior.label if prior else "prior"}, {"key": "current", "name": cur.label}], m["unit"])
    i = hier.index(nxt)
    return C.result(head, C.rows(mf.head(30), cols), ch, {"path": path, "level": nxt, "next_level": hier[i + 1] if i + 1 < len(hier) else None, "hierarchy": hierarchy,
                                                          "total": C.clean(tot["cur"]), "current_period": cur.to_dict()})


# ---------------------------------------------------------------- price / volume / mix
def pvm_calc(ctx, filters, cur, prior):
    mf = C.compare_frames(ctx, "sales", ["product_name"], filters, cur, prior)
    v1, v0, r1, r0, g1, g0 = (mf[c].values for c in ("units_c", "units_p", "revenue_c", "revenue_p", "gross_revenue_c", "gross_revenue_p"))
    sd = lambda a, b: np.where(b > 0, a / np.where(b > 0, b, 1), np.nan)
    p0, p1, l0, l1 = sd(r0, v0), sd(r1, v1), sd(g0, v0), sd(g1, v1)
    p0 = np.where(np.isnan(p0), p1, p0); p1 = np.where(np.isnan(p1), p0, p1)
    l0 = np.where(np.isnan(l0), l1, l0); l1 = np.where(np.isnan(l1), l0, l1)
    V1, V0 = v1.sum(), v0.sum()
    if V0 <= 0:
        raise ToolError("No volume in the comparison period; price/volume/mix cannot be computed.")
    s0 = v0 / V0
    price = (p1 - p0) * v1; lst = (l1 - l0) * v1; promo = price - lst
    vol = (V1 - V0) * s0 * p0; mix = (v1 - V1 * s0) * p0
    mf["list_price_effect"], mf["promo_effect"], mf["volume_effect"], mf["mix_effect"] = lst, promo, vol, mix
    mf["total"] = r1 - r0
    mf["list_price_change_pct"] = np.where(l0 > 0, (l1 / l0 - 1) * 100, np.nan)
    mf["units_change_pct"] = np.where(v0 > 0, (v1 / v0 - 1) * 100, np.nan)
    eff = {"volume": float(vol.sum()), "mix": float(mix.sum()), "list_price": float(lst.sum()), "promo_discount": float(promo.sum()), "total": float((r1 - r0).sum()),
           "units_change_pct": float((V1 / V0 - 1) * 100), "revenue_prior": float(r0.sum()), "revenue_current": float(r1.sum())}
    return mf, eff


def price_volume_mix(ctx, period=None, compare_to="prior_period", filters=None):
    cur, prior = _period_pair(period, compare_to, "last_12_weeks"); f = C.norm_filters(filters)
    if prior is None:
        raise ToolError("compare_to is required for price/volume/mix.")
    mf, e = pvm_calc(ctx, f, cur, prior)
    steps = [{"name": prior.label, "value": e["revenue_prior"], "total": True}, {"name": "Volume", "value": e["volume"]}, {"name": "Mix", "value": e["mix"]},
             {"name": "List price", "value": e["list_price"]}, {"name": "Promo / discount", "value": e["promo_discount"]}, {"name": cur.label, "value": e["revenue_current"], "total": True}]
    gap = e["total"]
    share = lambda v: C.clean(v / gap * 100, 0) if abs(gap) > 1e-9 else None
    head = (f"Revenue {cur.label} vs {prior.label}: {C.money(gap, True)}. Volume {C.money(e['volume'], True)}, mix {C.money(e['mix'], True)}, "
            f"list price {C.money(e['list_price'], True)}, promo/discount {C.money(e['promo_discount'], True)}.")
    mf = mf.reindex(mf.total.abs().sort_values(ascending=False).index)
    cols = ["product_name", "list_price_change_pct", "units_change_pct", "volume_effect", "mix_effect", "list_price_effect", "promo_effect", "total"]
    return C.result(head, C.rows(mf, cols), C.chart_waterfall("Price / volume / mix bridge", steps),
                    {**{k: C.clean(v) for k, v in e.items()}, "gap": C.clean(gap), "share_of_gap": {k: share(e[k]) for k in ("volume", "mix", "list_price", "promo_discount")},
                     "repriced": [{"product": r.product_name, "list_price_change_pct": C.clean(r.list_price_change_pct), "units_change_pct": C.clean(r.units_change_pct),
                                   "revenue_prior": C.clean(r.revenue_p), "units_prior": C.clean(r.units_p), "units_current": C.clean(r.units_c), "price_prior": C.clean(r.revenue_p / r.units_p) if r.units_p else None}
                                  for _, r in mf.iterrows() if pd.notna(r.list_price_change_pct) and abs(r.list_price_change_pct) >= 3],
                     "units_control_pct": C.clean(float(mf[(mf.list_price_change_pct.abs() < 3) | mf.list_price_change_pct.isna()].pipe(lambda d: (d.units_c.sum() / d.units_p.sum() - 1) * 100 if d.units_p.sum() else 0)))},
                    ["Price effect uses realised net price; it is split into list-price and promo/discount components. Mix is measured across products."])


# ---------------------------------------------------------------- driver decomposition
def _build_tree(df, levels, depth, total_gap, top_n, label, metric_cols):
    c, p = metric_cols
    node = {"label": label, "cur": C.clean(df[c].sum()), "prior": C.clean(df[p].sum()), "delta": C.clean(df[c].sum() - df[p].sum()), "children": []}
    node["pct"] = C.clean(node["delta"] / abs(node["prior"]) * 100) if node["prior"] else None
    node["share_of_gap"] = C.clean(node["delta"] / total_gap * 100) if abs(total_gap) > 1e-9 else None
    if depth >= len(levels):
        return node
    g = df.groupby(levels[depth])[[c, p]].sum()
    g["d"] = g[c] - g[p]
    g = g.reindex(g.d.abs().sort_values(ascending=False).index)
    for name, r in g.head(top_n).iterrows():
        child = _build_tree(df[df[levels[depth]] == name], levels, depth + 1, total_gap, top_n, str(name), metric_cols)
        child["dim"] = levels[depth]
        node["children"].append(child)
    if len(g) > top_n:
        rest = g.iloc[top_n:]
        node["children"].append({"label": f"Other ({len(rest)})", "dim": levels[depth], "cur": C.clean(rest[c].sum()), "prior": C.clean(rest[p].sum()), "delta": C.clean(rest.d.sum()),
                                 "pct": None, "share_of_gap": C.clean(rest.d.sum() / total_gap * 100) if abs(total_gap) > 1e-9 else None, "children": []})
    return node


def driver_decomposition(ctx, period=None, compare_to="prior_period", metric="revenue", filters=None, top_n=4):
    m = S.metric(metric)
    if m["source"] != "sales" or not m["additive"]:
        raise ToolError("driver_decomposition supports additive sales metrics: revenue or units.")
    cur, prior = _period_pair(period, compare_to)
    if prior is None:
        raise ToolError("compare_to is required for driver decomposition.")
    f = C.norm_filters(filters)
    mf = C.compare_frames(ctx, "sales", ["region", "channel", "segment", "product_name"], f, cur, prior)
    pm = C.product_map(); mf["category"] = mf.product_name.map(lambda p: pm[p]["category"])
    c, p = f"{metric}_c", f"{metric}_p"
    gap = float(mf[c].sum() - mf[p].sum()); base_p = float(mf[p].sum())
    conc, flat = {}, []
    for d in ["region", "category", "channel", "segment", "product_name"]:
        g = mf.groupby(d)[[c, p]].sum(); g["delta"] = g[c] - g[p]
        g = g.reindex(g.delta.abs().sort_values(ascending=False).index)
        for name, r in g.head(5).iterrows():
            sh = r.delta / gap * 100 if abs(gap) > 1e-9 else None
            pshare = r[p] / base_p * 100 if base_p else None
            flat.append({"dimension": d, "member": name, "delta": C.clean(r.delta), "share_of_gap": C.clean(sh), "prior_share_pct": C.clean(pshare),
                         "disproportion": C.clean(sh / pshare) if sh is not None and pshare else None, "pct_change": C.clean(r.delta / r[p] * 100) if r[p] else None})
        top = g.iloc[0]
        conc[d] = {"top_member": top.name, "top_delta": C.clean(top.delta), "top_share_of_gap": C.clean(top.delta / gap * 100) if abs(gap) > 1e-9 else None}
    ranked = sorted([d for d in ["region", "category", "channel", "segment"]], key=lambda d: -abs(conc[d]["top_share_of_gap"] or 0))
    l1 = ranked[0]; l2 = "product_name" if l1 == "category" else ranked[1]
    l3 = next(d for d in ranked if d not in (l1, l2))
    tree = _build_tree(mf, [l1, l2, l3], 0, gap, int(top_n), "Total change", (c, p))
    flat.sort(key=lambda r: -abs(r["delta"] or 0))
    steps = [{"name": prior.label, "value": base_p, "total": True}] + [{"name": ch["label"], "value": ch["delta"]} for ch in tree["children"]] + [{"name": cur.label, "value": float(mf[c].sum()), "total": True}]
    lead = flat[0]
    head = (f"{m['name']} {cur.label} vs {prior.label}: {C.fmt(metric, gap, True)} ({C.pct(gap / base_p * 100 if base_p else None)}). "
            f"Largest driver: {lead['member']} ({lead['dimension']}) at {C.fmt(metric, lead['delta'], True)} ({C.clean(lead['share_of_gap'], 0)}% of the gap).")
    facts = {"metric": metric, "gap": C.clean(gap), "gap_pct": C.clean(gap / base_p * 100) if base_p else None, "prior": C.clean(base_p), "current": C.clean(float(mf[c].sum())),
             "concentration": conc, "top_drivers": flat[:10], "tree": tree, "tree_levels": [l1, l2, l3], "current_period": cur.to_dict(), "prior_period": prior.to_dict()}
    if metric == "revenue":
        try:
            _, e = pvm_calc(ctx, f, cur, prior)
            facts["pvm"] = {k: C.clean(v) for k, v in e.items()}
        except ToolError:
            pass
    return C.result(head, flat[:12], C.chart_waterfall(f"{m['name']} gap by {l1}", steps, m["unit"]), facts,
                    ["Contributions are exact for additive metrics; driver shares can exceed 100% when other drivers offset."])


# ---------------------------------------------------------------- scorecard
def performance_scorecard(ctx, dimension, period=None, compare_to="prior_period", filters=None, limit=15):
    d = S.norm_dim(dimension)
    if d not in S.SALES_DIMS:
        raise ToolError(f"dimension must be one of {', '.join(S.SALES_DIMS)}.")
    cur, prior = _period_pair(period, compare_to); f = C.norm_filters(filters)
    mf = C.compare_frames(ctx, "sales", [d], f, cur, prior)
    T = {k: mf[k].sum() for k in mf.columns if k.endswith(("_c", "_p"))}
    out = pd.DataFrame({d: mf[d]})
    for k, key in [("revenue", "revenue"), ("units", "units")]:
        out[k] = mf[f"{key}_c"]; out[f"{k}_growth_pct"] = np.where(mf[f"{key}_p"] > 0, (mf[f"{key}_c"] / mf[f"{key}_p"] - 1) * 100, np.nan)
    out["revenue_share_pct"] = mf.revenue_c / T["revenue_c"] * 100
    out["avg_price"] = S._d(mf.revenue_c, mf.units_c)
    out["price_change_pct"] = (out.avg_price / S._d(mf.revenue_p, mf.units_p) - 1) * 100
    out["margin_pct"] = S.mcalc("gross_margin_pct", mf, "_c")
    out["margin_change_pp"] = out.margin_pct - S.mcalc("gross_margin_pct", mf, "_p")
    out["promo_share_pct"] = S.mcalc("promo_share", mf, "_c")
    tg = T["revenue_c"] - T["revenue_p"]
    out["contribution_to_growth_pp"] = (mf.revenue_c - mf.revenue_p) / T["revenue_p"] * 100 if T["revenue_p"] else np.nan
    out = out.sort_values("revenue", ascending=False).head(int(limit))
    best, worst = out.sort_values("revenue_growth_pct").iloc[-1], out.sort_values("revenue_growth_pct").iloc[0]
    head = (f"Scorecard by {d} ({cur.label} vs {prior.label if prior else 'n/a'}): total revenue {C.money(T['revenue_c'])} ({C.pct((T['revenue_c'] / T['revenue_p'] - 1) * 100 if T['revenue_p'] else None)}). "
            f"Fastest growth: {best[d]} ({C.pct(best.revenue_growth_pct)}); weakest: {worst[d]} ({C.pct(worst.revenue_growth_pct)}).")
    ch = C.chart_bar(f"Revenue growth % by {d}", [{"name": str(r[d]), "value": C.clean(r.revenue_growth_pct)} for _, r in out.iterrows()], [{"key": "value", "name": "Revenue growth %"}], "pct", signed=True)
    return C.result(head, C.rows(out), ch, {"total_revenue": C.clean(T["revenue_c"]), "total_gap": C.clean(tg), "best": best[d], "worst": worst[d], "current_period": cur.to_dict()})


# ---------------------------------------------------------------- anomaly detection
def expected_vs_actual(values, eval_n, lookback=26, base_n=8):
    """Seasonally-adjusted expected value for the last eval_n weeks, using a frozen pre-window baseline."""
    v = np.asarray(values, dtype=float); n = len(v); w0 = n - eval_n
    if w0 - base_n < 0:
        return None
    base0 = v[w0 - base_n:w0].mean()
    have_py = w0 - base_n - 52 >= 0
    pyb = v[w0 - base_n - 52:w0 - 52].mean() if have_py else None

    def exp_at(t, b):
        if have_py and t - 52 >= 0 and pyb and pyb > 0:
            return b * float(np.clip(v[t - 52] / pyb, .6, 1.6))
        return b
    exp = np.array([exp_at(t, base0) for t in range(w0, n)])
    resid = []
    for t in range(max(base_n + 1, w0 - lookback), w0):
        b = v[t - base_n:t].mean()
        pyb_t = v[t - base_n - 52:t - 52].mean() if t - base_n - 52 >= 0 else None
        e = b * float(np.clip(v[t - 52] / pyb_t, .6, 1.6)) if pyb_t and pyb_t > 0 and t - 52 >= 0 else b
        if e > 0:
            resid.append((v[t] - e) / e)
    sigma = max(float(np.std(resid)) if len(resid) > 5 else .05, .02)
    act = v[w0:]
    dev = np.where(exp > 0, (act - exp) / exp, 0)
    return {"expected": exp, "actual": act, "dev": dev, "z": dev / sigma, "sigma": sigma}


def weekly_matrix(ctx, metric, dim=None, filters=None):
    """Full-history weekly series: returns (weeks_index, {member: np.array})."""
    m = S.metric(metric); ao = C.as_of(); start = C.data_min()
    df = C.fetch(ctx, m["source"], ["week_start", *([dim] if dim else [])], filters or {}, start, ao)
    df["v"] = S.mcalc(metric, df)
    wk = pd.date_range(start, ao, freq="7D").strftime("%Y-%m-%d")
    out = {}
    for key, g in (df.groupby(dim) if dim else [("Total", df)]):
        s = g.set_index(g.week_start.astype(str).str[:10]).v.reindex(wk)
        out[key] = s.ffill().bfill().fillna(0).values
    return wk, out


def anomaly_detection(ctx, metric="revenue", group_by=None, filters=None, eval_weeks=8, lookback_weeks=26, z_threshold=2.5):
    m = S.metric(metric); f = C.norm_filters(filters); gb = _gb(group_by, 1); eval_weeks = max(2, min(int(eval_weeks), 26))
    wk, mat = weekly_matrix(ctx, metric, gb[0] if gb else None, f)
    flagged, summary = [], []
    for key, v in mat.items():
        r = expected_vs_actual(v, eval_weeks, int(lookback_weeks))
        if r is None:
            continue
        weeks_ev = wk[-eval_weeks:]
        hits = [i for i in range(eval_weeks) if abs(r["z"][i]) >= z_threshold]
        for i in hits:
            flagged.append({"group": key, "week": weeks_ev[i], "actual": C.clean(r["actual"][i]), "expected": C.clean(r["expected"][i]), "deviation_pct": C.clean(r["dev"][i] * 100), "z": C.clean(r["z"][i])})
        if hits:
            summary.append({"group": key, "flagged_weeks": len(hits), "worst_z": C.clean(r["z"][max(hits, key=lambda i: abs(r["z"][i]))]), "avg_dev_pct": C.clean(np.mean(r["dev"][hits]) * 100)})
    summary.sort(key=lambda r: -abs(r["worst_z"]))
    if gb:
        ex = next(iter(mat))
    ctx.periods.append(C.Period(pd.Timestamp(wk[-eval_weeks]).date(), C.as_of(), f"last {eval_weeks} weeks", "weeks"))
    if not flagged:
        head = f"No {m['name']} anomalies beyond |z|≥{z_threshold} in the last {eval_weeks} weeks versus the seasonally-adjusted baseline."
        ch = None
    else:
        top = summary[0]
        head = (f"{len(summary)} {'group' if gb else 'series'}(s) show unusual {m['name']} in the last {eval_weeks} weeks versus a seasonally-adjusted baseline; "
                f"strongest: {top['group']} ({C.pct(top['avg_dev_pct'])} average deviation, z={top['worst_z']}).")
        key0 = top["group"]; r = expected_vs_actual(mat[key0], eval_weeks, int(lookback_weeks))
        data = [{"name": wk[-eval_weeks + i], "actual": C.clean(r["actual"][i]), "expected": C.clean(r["expected"][i])} for i in range(eval_weeks)]
        ch = C.chart_line(f"{m['name']}: actual vs expected — {key0}", data, [{"key": "actual", "name": "Actual"}, {"key": "expected", "name": "Expected (seasonal baseline)"}], m["unit"])
    return C.result(head, flagged[:40] if flagged else [], ch, {"summary": summary[:10], "z_threshold": z_threshold, "eval_weeks": eval_weeks},
                    ["Baseline = pre-window 8-week level adjusted by the prior-year seasonal pattern; sensitivity set by z-threshold."])
