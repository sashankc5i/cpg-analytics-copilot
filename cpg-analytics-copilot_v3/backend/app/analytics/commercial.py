"""Promotions, pricing, competitor, assortment, cohorts (CPG-004/007/008/009/010/015/016, DEC-006)."""
from datetime import date, timedelta
from statistics import NormalDist

import numpy as np
import pandas as pd

from .. import semantic as S
from ..db import fetch_df
from . import core as C
from .errors import PolicyError, ToolError

W = timedelta(weeks=1)


def _d(s):
    return date.fromisoformat(str(s)[:10])


def _inter(a, b):
    return b if not a else [x for x in a if x in b]


# =============================================================== promotions
def _analyze_event(ctx, ev, f):
    start, end = _d(ev.start_week), _d(ev.end_week); ao = C.as_of()
    nwk = (end - start).days // 7 + 1
    ef = {k: list(v) for k, v in f.items()}
    for dim in ("region", "channel"):
        val = getattr(ev, dim)
        if val != "All":
            ef[dim] = _inter(ef.get(dim), [val])
            if not ef[dim]:
                return None
    sibs = [s for s in str(ev.siblings or "").split(",") if s]
    ef["product_name"] = [ev.product_name] + sibs
    pre_s, post_e = start - 4 * W, min(end + 2 * W, ao)
    df = C.fetch(ctx, "sales", ["week_start", "product_name"], ef, pre_s, post_e)
    if df.empty:
        return None
    df["wk"] = df.week_start.astype(str).str[:10]

    def series(prod, col):
        s = df[df.product_name == prod].set_index("wk")[col]
        return s
    effects, out = [], {"promo_id": ev.promo_id, "product": ev.product_name, "region": ev.region, "channel": ev.channel, "start": ev.start_week[:10], "end": ev.end_week[:10],
                        "discount_pct": C.clean(ev.discount_pct * 100, 1), "mechanic": ev.mechanic, "weeks": nwk}
    wks_pre = [(start - i * W).isoformat() for i in range(4, 0, -1)]
    wks_dur = [(start + i * W).isoformat() for i in range(nwk)]
    wks_post = [(end + i * W).isoformat() for i in (1, 2) if end + i * W <= ao]
    u, r, g = (series(ev.product_name, c) for c in ("units", "revenue", "gross_revenue"))
    pre_u = u.reindex(wks_pre).dropna(); pre_r = r.reindex(wks_pre).dropna()
    if len(pre_u) < 2:
        return None
    bu, bsd, br = pre_u.mean(), pre_u.std(ddof=1), pre_r.mean()
    dur_u, dur_r = u.reindex(wks_dur).fillna(0), r.reindex(wks_dur).fillna(0)
    for w in wks_dur:
        effects.append({"week": w, "promo_id": ev.promo_id, "kind": "lift", "revenue": float(dur_r[w] - br), "units": float(dur_u[w] - bu)})
    inc_u, inc_r = float(dur_u.sum() - bu * nwk), float(dur_r.sum() - br * nwk)
    disc_cost = float(g.reindex(wks_dur).fillna(0).sum() - dur_r.sum())
    post_u, post_r = u.reindex(wks_post).fillna(0), r.reindex(wks_post).fillna(0)
    post_loss_r = post_loss_u = 0.0
    for w in wks_post:
        effects.append({"week": w, "promo_id": ev.promo_id, "kind": "post_dip", "revenue": float(post_r[w] - br), "units": float(post_u[w] - bu)})
    if wks_post:
        post_loss_u, post_loss_r = min(0.0, float((post_u - bu).sum())), min(0.0, float((post_r - br).sum()))
    can_u = can_r = 0.0; sib_rows = []
    for sb in sibs:
        su, sr = series(sb, "units"), series(sb, "revenue")
        spre_u, spre_r = su.reindex(wks_pre).dropna(), sr.reindex(wks_pre).dropna()
        if len(spre_u) < 2:
            continue
        sdu, sdr = su.reindex(wks_dur).fillna(0), sr.reindex(wks_dur).fillna(0)
        for w in wks_dur:
            effects.append({"week": w, "promo_id": ev.promo_id, "kind": "cannibalisation", "revenue": float(min(0, sdr[w] - spre_r.mean())), "units": float(min(0, sdu[w] - spre_u.mean()))})
        du, dr = float(sdu.sum() - spre_u.mean() * nwk), float(sdr.sum() - spre_r.mean() * nwk)
        sib_rows.append({"product": sb, "change_pct": C.clean((sdu.mean() / spre_u.mean() - 1) * 100), "units_delta": C.clean(du)})
        can_u += min(0.0, du); can_r += min(0.0, dr)
    out.update({"baseline_units_wk": C.clean(bu, 0), "during_units_wk": C.clean(dur_u.mean(), 0), "lift_pct": C.clean((dur_u.mean() / bu - 1) * 100 if bu else None),
                "incremental_units": C.clean(inc_u, 0), "incremental_revenue": C.clean(inc_r, 0),
                "incremental_units_range": [C.clean(float(dur_u.sum() - (bu + bsd) * nwk), 0), C.clean(float(dur_u.sum() - (bu - bsd) * nwk), 0)],
                "discount_cost": C.clean(disc_cost, 0), "post_promo_loss_revenue": C.clean(post_loss_r, 0), "cannibalised_revenue": C.clean(can_r, 0), "cannibalised_units": C.clean(can_u, 0),
                "net_incremental_revenue": C.clean(inc_r + post_loss_r + can_r, 0), "cannibalisation_ratio_pct": C.clean(-can_u / inc_u * 100) if inc_u > 0 and can_u < 0 else 0,
                "siblings": sib_rows, "roi": C.clean((inc_r + post_loss_r + can_r) / disc_cost, 2) if disc_cost > 0 else None})
    return out, effects


def promotion_analysis(ctx, analysis="impact", period=None, compare_to="prior_period", filters=None):
    if analysis not in ("impact", "lift", "cannibalization"):
        raise ToolError("analysis must be impact, lift or cannibalization.")
    cur = C.resolve_period(period or "last_12_weeks"); prior = C.shift(cur, compare_to if compare_to != "none" else "prior_period"); f = C.norm_filters(filters)
    ctx.periods += [cur, prior]
    ev = fetch_df("SELECT * FROM fact_promotions")
    ev = ev[(ev.end_week.map(_d) >= prior.start) & (ev.start_week.map(_d) <= cur.end)]
    if "product_name" in f:
        ev = ev[ev.product_name.isin(f["product_name"])]
    if "category" in f:
        ev = ev[ev.category.isin(f["category"])]
    ctx.tables.add("fact_promotions")
    events, eff = [], []
    for ev_ in ev.itertuples():
        r = _analyze_event(ctx, ev_, {k: v for k, v in f.items() if k not in ("product_name", "category", "brand")})
        if r:
            events.append(r[0]); eff += r[1]
    mf, tot = C.compare_table(ctx, "promo_share", [], f, cur, prior)
    ps_c, ps_p = tot["cur"], tot["prior"]

    def window(p, kinds=None):
        return sum(e["revenue"] for e in eff if p.start <= _d(e["week"]) <= p.end and (kinds is None or e["kind"] in kinds))
    scale = cur.weeks / prior.weeks if prior.weeks else 1
    cur_all, pri_all = window(cur), window(prior) * scale
    cur_lift, pri_lift = window(cur, ["lift"]), window(prior, ["lift"]) * scale
    cur_dip, cur_can = window(cur, ["post_dip"]), window(cur, ["cannibalisation"])
    pri_can = window(prior, ["cannibalisation"]) * scale
    last_promo_week = max([e["end"] for e in events], default=None)
    facts = {"promo_share_cur": C.clean(ps_c), "promo_share_prior": C.clean(ps_p), "effect_cur": C.clean(cur_all), "effect_prior_scaled": C.clean(pri_all), "effect_delta": C.clean(cur_all - pri_all),
             "lift_cur": C.clean(cur_lift), "lift_prior_scaled": C.clean(pri_lift), "post_dip_cur": C.clean(cur_dip), "cannibal_cur": C.clean(cur_can), "cannibal_prior_scaled": C.clean(pri_can),
             "events": events, "n_events": len(events), "last_promo_end": last_promo_week,
             "weekly_effects": [{**e, "revenue": C.clean(e["revenue"], 0), "units": C.clean(e["units"], 0)} for e in eff], "current_period": cur.to_dict(), "prior_period": prior.to_dict()}
    if not events:
        return C.result(f"No promotions overlapped {prior.label} to {cur.label} in this scope.", [], None, facts)
    ev_sorted = sorted(events, key=lambda e: -(e["incremental_revenue"] or 0))
    if analysis == "impact":
        cols = ["promo_id", "product", "region", "channel", "start", "end", "discount_pct", "lift_pct", "incremental_revenue", "discount_cost", "post_promo_loss_revenue", "cannibalised_revenue", "net_incremental_revenue", "roi"]
        head = (f"{len(events)} promotion(s) overlapped {prior.label}–{cur.label}. Promo share of revenue {C.pct(ps_c, False)} vs {C.pct(ps_p, False)}. "
                f"Estimated promotion effect on revenue: {C.money(cur_all, True)} in {cur.label} vs {C.money(pri_all, True)} in the prior window (scaled), a swing of {C.money(cur_all - pri_all, True)}.")
    elif analysis == "lift":
        cols = ["promo_id", "product", "region", "start", "end", "baseline_units_wk", "during_units_wk", "lift_pct", "incremental_units", "incremental_revenue", "incremental_units_range"]
        t = ev_sorted[0]
        head = f"Largest measured lift: {t['promo_id']} {t['product']} at {C.pct(t['lift_pct'])} units lift vs the 4-week pre-promo baseline ({C.fnum(t['incremental_units'], True)} incremental units, {C.money(t['incremental_revenue'], True)})."
    else:
        cols = ["promo_id", "product", "start", "end", "lift_pct", "incremental_units", "cannibalised_units", "cannibalisation_ratio_pct", "siblings"]
        wc = [e for e in events if e["siblings"]]
        head = ("; ".join(f"{e['promo_id']} {e['product']}: {', '.join(s['product'] + ' ' + C.pct(s['change_pct']) for s in e['siblings'])}, ~{C.clean(e['cannibalisation_ratio_pct'], 0)}% of the incremental units" for e in wc[:3])
                or "No promoted products with tracked substitutes in scope.")
    ch = C.chart_bar("Incremental revenue by promotion (vs pre-promo baseline)", [{"name": f"{e['promo_id']} {e['product']}", "value": e["incremental_revenue"], "net": e["net_incremental_revenue"]} for e in ev_sorted],
                     [{"key": "value", "name": "Incremental revenue"}, {"key": "net", "name": "Net of dip & cannibalisation"}], "currency", signed=True)
    return C.result(head, [{k: e.get(k) for k in cols} for e in ev_sorted], ch, facts,
                    ["Baseline = mean of the 4 weeks before each promotion; seasonality and trend are not removed, so lift is indicative.",
                     "Cannibalisation is measured on tracked same-subcategory substitutes only."])


# =============================================================== elasticity & pricing
def _ols(X, y):
    XtX = np.linalg.pinv(X.T @ X); b = XtX @ X.T @ y; res = y - X @ b
    dof = max(len(y) - X.shape[1], 1); s2 = (res @ res) / dof
    se = np.sqrt(np.clip(np.diag(XtX) * s2, 0, None)); r2 = 1 - (res @ res) / ((y - y.mean()) @ (y - y.mean()))
    return b, se, r2


def _elasticity_one(ctx, product, seg, f, start, end, cur_scope_filters):
    ff = {**f, "product_name": [product]}
    if seg:
        ff["segment"] = [seg]
    df = C.fetch(ctx, "sales", ["week_start"], ff, start, end)
    inv = C.fetch(ctx, "inventory", ["week_start"], {k: v for k, v in ff.items() if k in S.INV_DIMS}, start, end)
    df = df.merge(inv[["week_start", "stockout_days", "pr_weeks"]], on="week_start", how="left").sort_values("week_start")
    df = df[(df.units > 0)]
    if len(df) < 30:
        return None
    lp = (df.gross_revenue / df.units).values
    var = float((lp.max() - lp.min()) / lp.mean() * 100)
    t = np.arange(len(df)); w = 2 * np.pi * t / 52
    X = np.column_stack([np.ones(len(df)), np.log(lp), df.promo_units.values / df.units.values, (df.stockout_days / (7 * df.pr_weeks.clip(lower=1))).fillna(0).values, np.sin(w), np.cos(w), t / 52])
    if np.std(np.log(lp)) < 0.005:
        return {"product": product, "segment": seg or "All", "elasticity": None, "price_variation_pct": C.clean(var), "verdict": "not identifiable (no price variation)", "n_weeks": len(df)}
    b, se, r2 = _ols(X, np.log(df.units.values))
    e, s = float(b[1]), float(se[1])
    lo, hi = e - 1.96 * s, e + 1.96 * s
    verdict = "inconclusive (interval spans zero)" if lo <= 0 <= hi else ("elastic (demand falls faster than price rises)" if e < -1 else "inelastic" if e < 0 else "implausible sign")
    return {"product": product, "segment": seg or "All", "elasticity": C.clean(e), "se": C.clean(s), "ci_low": C.clean(lo), "ci_high": C.clean(hi), "r2": C.clean(r2), "n_weeks": len(df),
            "price_variation_pct": C.clean(var), "verdict": verdict}


def price_elasticity(ctx, product_name=None, filters=None, period="all", by_segment=True):
    ff = dict(filters or {})
    if product_name:
        ff["product_name"] = product_name
    f = C.norm_filters(ff); cur = C.resolve_period(period); ctx.periods.append(cur)
    prods = f.pop("product_name", None) or C.dim_values()["product_name"]
    rows_ = []
    for p in prods[:12]:
        r = _elasticity_one(ctx, p, None, f, cur.start, cur.end, f)
        if r:
            rows_.append(r)
        if by_segment and len(prods) <= 3 and r and r["elasticity"] is not None:
            for sg in C.dim_values()["segment"]:
                rs = _elasticity_one(ctx, p, sg, f, cur.start, cur.end, f)
                if rs:
                    rows_.append(rs)
    if not rows_:
        raise ToolError("Not enough weekly history to estimate elasticity for this scope.")
    ident = [r for r in rows_ if r["elasticity"] is not None and "inconclusive" not in r["verdict"]]
    head = (f"Estimated price elasticity for {len(rows_)} series; {len(ident)} statistically identifiable. " +
            (f"Example: {ident[0]['product']} ({ident[0]['segment']}) {ident[0]['elasticity']} (95% CI {ident[0]['ci_low']} to {ident[0]['ci_high']}), {ident[0]['verdict']}." if ident else "None had enough price variation to conclude."))
    data = [{"name": f"{r['product']} / {r['segment']}", "value": r["elasticity"]} for r in rows_ if r["elasticity"] is not None]
    return C.result(head, rows_, C.chart_bar("Price elasticity of demand (log-log, with 95% CI in table)", data, [{"key": "value", "name": "Elasticity"}], "ratio", signed=True) if data else None,
                    {"estimates": rows_}, ["Log-log regression of weekly units on list price with promo, stockout, seasonality and trend controls. Observational: treat as indicative, not causal."])


def price_optimization(ctx, product_name, filters=None, min_volume_change_pct=-10.0, assumed_elasticity=None):
    f = C.norm_filters({**(filters or {}), "product_name": product_name}); prod = f["product_name"][0]
    el = price_elasticity(ctx, product_name=prod, filters={k: v for k, v in f.items() if k != "product_name"}, by_segment=False)
    est = el["facts"]["estimates"][0]
    assumed = False
    if est["elasticity"] is None or "inconclusive" in est["verdict"] or est["elasticity"] >= 0:
        if assumed_elasticity is None:
            raise ToolError(f"Elasticity for {prod} is not statistically reliable ({est['verdict']}); price optimisation was withheld. Provide assumed_elasticity explicitly to run a what-if.")
        e, se, assumed = float(assumed_elasticity), 0.3, True
    else:
        e, se = est["elasticity"], est["se"]
    ao = C.as_of(); s = ao - 7 * W
    cur = C.fetch(ctx, "sales", [], f, s, ao); ctx.periods.append(C.Period(s, ao, "last 8 weeks", "weeks"))
    units_wk = cur.units.iloc[0] / max(cur.n_weeks.iloc[0], 1); lp = cur.gross_revenue.iloc[0] / cur.units.iloc[0]; cost = cur.cogs.iloc[0] / cur.units.iloc[0]
    if cur.units.iloc[0] <= 0:
        raise ToolError("No recent volume for this product in scope.")
    rows_ = []
    for chg in np.arange(-10, 10.1, 2.5):
        r = {"price_change_pct": float(chg)}
        for tag, ee in (("mid", e), ("lo", e - 1.96 * se), ("hi", e + 1.96 * se)):
            u = units_wk * (1 + chg / 100) ** ee
            r[f"units_{tag}"] = u; r[f"margin_{tag}"] = (lp * (1 + chg / 100) - cost) * u; r[f"revenue_{tag}"] = lp * (1 + chg / 100) * u
        r["units_change_pct"] = (r["units_mid"] / units_wk - 1) * 100
        rows_.append(r)
    base_m = rows_[4]["margin_mid"]
    feas = [r for r in rows_ if r["units_change_pct"] >= min_volume_change_pct]
    best = max(feas, key=lambda r: r["margin_mid"])
    robust = best["margin_lo"] >= base_m * 0.98 and best["margin_hi"] >= base_m * 0.98 and best["price_change_pct"] != 0
    head = (f"{prod}: modelled optimum under a {min_volume_change_pct:.0f}% volume floor is a {best['price_change_pct']:+.1f}% price move "
            f"({C.pct(best['units_change_pct'])} units, weekly gross margin {C.money(best['margin_mid'] - base_m, True)}). "
            + ("The gain holds across the elasticity uncertainty range." if robust else "Not robust across the elasticity uncertainty range; treat as a hypothesis to test, not a recommendation."))
    data = [{"name": f"{r['price_change_pct']:+.1f}%", "mid": C.clean(r["margin_mid"], 0), "lo": C.clean(r["margin_lo"], 0), "hi": C.clean(r["margin_hi"], 0)} for r in rows_]
    return C.result(head, [{k: C.clean(v) for k, v in r.items()} for r in rows_],
                    C.chart_line(f"Weekly gross margin vs price change — {prod}", data, [{"key": "mid", "name": "Central estimate"}, {"key": "lo", "name": "Elasticity low"}, {"key": "hi", "name": "Elasticity high"}], "currency"),
                    {"product": prod, "elasticity": C.clean(e), "assumed": assumed, "best_change_pct": best["price_change_pct"], "robust": bool(robust), "base_weekly_margin": C.clean(base_m), "base_units_wk": C.clean(units_wk)},
                    ["Constant-elasticity what-if on the last 8 weeks. Excludes competitor reaction, promotions, and cross-product effects.", "Assumed elasticity used." if assumed else "Elasticity estimated from history."])


# =============================================================== competitor signals
def competitor_signals(ctx, category=None, period=None, compare_to="prior_period"):
    cur = C.resolve_period(period or "last_8_weeks"); prior = C.shift(cur, compare_to if compare_to != "none" else "prior_period"); ctx.periods += [cur, prior]
    f = C.norm_filters({"category": category} if category else {})
    allowed = _inter(f.get("category"), ctx.scope.get("category")) if ctx.scope.get("category") else (f.get("category") or C.dim_values()["category"])
    ctx.tables.add("fact_competitor")
    comp = fetch_df("SELECT week_start, category, price_index, promo_intensity FROM fact_competitor")
    comp["wk"] = comp.week_start.astype(str).str[:10]
    have = set(comp.category.unique())
    out, missing = [], [c for c in allowed if c not in have]
    for cat in [c for c in allowed if c in have]:
        cc = comp[comp.category == cat]
        a = cc[(cc.wk >= cur.start.isoformat()) & (cc.wk <= cur.end.isoformat())]; b = cc[(cc.wk >= prior.start.isoformat()) & (cc.wk <= prior.end.isoformat())]
        sales = C.fetch(ctx, "sales", ["week_start"], {**{k: v for k, v in f.items() if k != "category"}, "category": [cat]}, C.data_min(), C.as_of()).sort_values("week_start")
        sales["wk"] = sales.week_start.astype(str).str[:10]
        j = sales.merge(cc, on="wk")
        corr = coef = None
        if len(j) > 30:
            t = np.arange(len(j)); w = 2 * np.pi * t / 52
            X = np.column_stack([np.ones(len(j)), t / 52, np.sin(w), np.cos(w), j.promo_intensity.values])
            bb, se, _ = _ols(X, np.log(j.units.clip(lower=1).values))
            coef = float(bb[4]); corr = float(np.corrcoef(j.promo_intensity, np.log(j.units.clip(lower=1)) - np.polyval(np.polyfit(t, np.log(j.units.clip(lower=1)), 1), t))[0, 1])
        d_promo = float(a.promo_intensity.mean() - b.promo_intensity.mean()) if len(a) and len(b) else None
        cur_rev = float(sales[(sales.wk >= cur.start.isoformat()) & (sales.wk <= cur.end.isoformat())].revenue.sum())
        est = (coef * d_promo) if coef is not None and d_promo is not None else None
        out.append({"category": cat, "competitor_promo_intensity": C.clean(a.promo_intensity.mean(), 3), "prior_promo_intensity": C.clean(b.promo_intensity.mean(), 3), "promo_delta": C.clean(d_promo, 3),
                    "price_index": C.clean(a.price_index.mean(), 3), "prior_price_index": C.clean(b.price_index.mean(), 3), "corr_with_our_units": C.clean(corr), "units_response_per_unit_intensity": C.clean(coef),
                    "est_units_effect_pct": C.clean(est * 100) if est is not None else None, "est_revenue_effect": C.clean(est * cur_rev) if est is not None else None})
    if not out:
        raise ToolError(f"No governed competitor signal exists for: {', '.join(missing) or 'the requested scope'}. This evidence is unavailable.")
    big = max(out, key=lambda r: abs(r["promo_delta"] or 0))
    head = (f"Competitor promo intensity changed most in {big['category']} ({big['prior_promo_intensity']} → {big['competitor_promo_intensity']}; price index {big['prior_price_index']} → {big['price_index']}). "
            f"Association with our units: correlation {big['corr_with_our_units']}; implied effect {C.pct(big['est_units_effect_pct'])} of units." +
            (f" No external signal available for: {', '.join(missing)}." if missing else ""))
    ch = C.chart_bar("Competitor promo intensity: prior vs current", [{"name": r["category"], "prior": r["prior_promo_intensity"], "current": r["competitor_promo_intensity"]} for r in out],
                     [{"key": "prior", "name": prior.label}, {"key": "current", "name": cur.label}], "ratio")
    return C.result(head, out, ch, {"categories": out, "missing_categories": missing}, ["External signal (MarketScan feed, synthetic). Relationships are correlational, not causal.", *([f"No competitor data for {', '.join(missing)}."] if missing else [])])


# =============================================================== assortment & cohorts
def assortment_analysis(ctx, period=None, compare_to="prior_period", filters=None):
    cur = C.resolve_period(period or "last_12_weeks"); prior = C.shift(cur, compare_to if compare_to != "none" else "prior_period"); f = C.norm_filters(filters)
    mf = C.compare_frames(ctx, "sales", ["product_name", "region", "channel"], f, cur, prior)
    pm = C.product_map()
    g = mf.groupby("product_name").agg(revenue=("revenue_c", "sum"), prior=("revenue_p", "sum"), cogs=("cogs_c", "sum"), cells=("units_c", lambda s: int((s > 0).sum())), units=("units_c", "sum")).reset_index()
    g["category"] = g.product_name.map(lambda p: pm[p]["category"]); g = g.sort_values("revenue", ascending=False)
    tot = g.revenue.sum()
    g["share_pct"] = g.revenue / tot * 100; g["cum_share_pct"] = g.share_pct.cumsum()
    g["abc"] = np.where(g.cum_share_pct - g.share_pct < 70, "A", np.where(g.cum_share_pct - g.share_pct < 90, "B", "C"))
    g["growth_pct"] = np.where(g.prior > 0, (g.revenue / g.prior - 1) * 100, np.nan)
    g["margin_pct"] = (g.revenue - g.cogs) / g.revenue * 100
    max_cells = g.cells.max(); g["distribution_pct"] = g.cells / max_cells * 100
    g["flag"] = np.where((g.abc == "C") & (g.growth_pct < 0), "Tail & declining: review", np.where((g.abc == "A") & (g.growth_pct < -3), "Core & declining: investigate", np.where((g.abc != "A") & (g.growth_pct > 8), "Rising: candidate to expand", "")))
    a = g[g.abc == "A"]
    head = (f"{len(a)} product(s) generate ~70% of revenue ({', '.join(a.product_name.head(3))}). "
            f"{int((g.abc == 'C').sum())} tail product(s) contribute {g[g.abc == 'C'].share_pct.sum():.1f}%. Flags: {int((g.flag != '').sum())}.")
    ch = C.chart_bar("Product share of revenue (Pareto order)", [{"name": r.product_name, "value": C.clean(r.share_pct)} for r in g.itertuples()], [{"key": "value", "name": "Share of revenue %"}], "pct")
    return C.result(head, C.rows(g, ["product_name", "category", "revenue", "share_pct", "cum_share_pct", "abc", "growth_pct", "margin_pct", "distribution_pct", "flag"]), ch,
                    {"core": a.product_name.tolist(), "flags": g[g.flag != ""][["product_name", "flag"]].to_dict("records")}, ["ABC classes: A = first 70% of cumulative revenue, B = next 20%, C = last 10%."])


def customer_cohorts(ctx, segment=None):
    extra = [k for k in ctx.scope if k != "segment"]
    if extra:
        raise PolicyError("Cohort data cannot be restricted by " + ", ".join(extra) + "; it is unavailable under your data-access policy.")
    ctx.tables.add("fact_cohorts")
    df = fetch_df("SELECT * FROM fact_cohorts")
    segs = C.dim_values()["segment"]
    if ctx.scope.get("segment"):
        segs = ctx.scope["segment"]
    if segment:
        segs = [s for s in segs if s.lower() == segment.lower()] or segs
    df = df[df.segment.isin(segs)]; df["ret"] = df.active_customers / df.cohort_size * 100
    months = sorted(df.cohort_month.unique()); recent = months[-6:]; older = months[:-6]
    rows_ = []
    for sg in segs:
        for lab, ms in (("older cohorts", older), ("last 6 cohorts", recent)):
            d = df[(df.segment == sg) & df.cohort_month.isin(ms)]
            r = {"segment": sg, "group": lab}
            for k in (1, 3):
                v = d[d.months_since == k].ret
                r[f"retention_m{k}"] = C.clean(v.mean()) if len(v) else None
            rows_.append(r)
    worse = [r for r in rows_ if r["group"] == "last 6 cohorts"]
    base = {r["segment"]: r for r in rows_ if r["group"] == "older cohorts"}
    drops = [(r["segment"], (r["retention_m1"] or 0) - (base[r["segment"]]["retention_m1"] or 0)) for r in worse if r["retention_m1"] is not None and base[r["segment"]]["retention_m1"] is not None]
    drops.sort(key=lambda t: t[1])
    head = f"Month-1 retention by segment compared across cohort vintages. " + (f"Largest deterioration: {drops[0][0]} ({drops[0][1]:+.1f} pp for the last 6 cohorts vs older)." if drops else "")
    heat = df[(df.segment == segs[0])].pivot(index="cohort_month", columns="months_since", values="ret").round(1).tail(12)
    data = [{"name": f"M{k}", **{f"{sg}": C.clean(df[(df.segment == sg) & (df.cohort_month.isin(recent)) & (df.months_since == k)].ret.mean()) for sg in segs}} for k in range(0, 7)]
    return C.result(head, rows_, C.chart_line("Retention curve — last 6 cohorts by segment (%)", data, [{"key": sg, "name": sg} for sg in segs], "pct"),
                    {"rows": rows_, "worst": drops[0] if drops else None, "heatmap_segment": segs[0], "heatmap": {str(k): v for k, v in heat.to_dict("index").items()}},
                    ["Cohort data is customer-level from CRM and is not available by region/channel."])
