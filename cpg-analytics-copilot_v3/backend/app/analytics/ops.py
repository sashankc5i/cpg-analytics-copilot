"""Operations analytics: stockouts, inventory optimisation, forecasting, data quality & freshness."""
from datetime import date, datetime, timedelta, timezone
from statistics import NormalDist

import numpy as np
import pandas as pd

from .. import semantic as S
from ..db import engine, fetch_df
from . import core as C
from .errors import ToolError

W = timedelta(weeks=1)


# =============================================================== stockouts
def stockout_analysis(ctx, period=None, compare_to="prior_period", group_by=None, filters=None):
    cur = C.resolve_period(period or "last_4_weeks"); prior = C.shift(cur, compare_to if compare_to != "none" else "prior_period"); f = C.norm_filters(filters)
    inv_f = {k: v for k, v in f.items() if k in S.INV_DIMS}
    if len(inv_f) != len(f):
        ctx.warn("Channel/segment filters do not apply to availability data (measured at product-region level); inventory figures ignore them.")
    gb = [S.norm_dim(g) for g in (group_by or [])]
    mf = C.compare_frames(ctx, "inventory", ["product_name", "region"], inv_f, cur, prior)
    t = C.totals(mf, "inventory")
    rc, rp = float(S.mcalc("stockout_rate", t, "_c")[0]), float(S.mcalc("stockout_rate", t, "_p")[0])
    mf["rate_c"], mf["rate_p"] = S.mcalc("stockout_rate", mf, "_c"), S.mcalc("stockout_rate", mf, "_p")
    s0 = (prior.start if prior else cur.start) - 8 * W
    sales = C.fetch(ctx, "sales", ["week_start", "product_name", "region"], f, s0, cur.end)
    inv = C.fetch(ctx, "inventory", ["week_start", "product_name", "region"], inv_f, s0, cur.end)
    key = ["product_name", "region"]
    d = sales.merge(inv[["week_start", *key, "stockout_days"]], on=["week_start", *key], how="left").fillna({"stockout_days": 0}).sort_values([*key, "week_start"])
    d["wk"] = d.week_start.astype(str).str[:10]
    d["u_ok"] = d.units.where(d.stockout_days == 0)
    d["base_u"] = d.groupby(key).u_ok.transform(lambda s: s.shift(1).rolling(8, min_periods=2).mean())  # fallback baseline
    # Preferred baseline: peer-region method (controls for seasonality/trend): expected = historical ratio x same-week units of regions without stockouts
    for p_, g in d.groupby("product_name"):
        U = g.pivot_table(index="wk", columns="region", values="units", aggfunc="sum"); Sd = g.pivot_table(index="wk", columns="region", values="stockout_days", aggfunc="sum").reindex_like(U).fillna(0)
        if U.shape[1] < 3:
            continue
        Um = U.where(Sd == 0)
        for r_ in U.columns:
            peer = Um.drop(columns=r_).mean(axis=1)
            rho = (U[r_] / peer).where(Sd[r_] == 0).median()
            if pd.isna(rho):
                continue
            exp = (rho * peer)
            m_ = (d.product_name == p_) & (d.region == r_)
            d.loc[m_, "base_u"] = d.loc[m_, "wk"].map(exp).fillna(d.loc[m_, "base_u"])
    d["price"] = (d.revenue / d.units.replace(0, np.nan))
    d["price"] = d.price.fillna(d.groupby(key).price.transform("mean")).fillna(0)
    d["lost_u"] = np.where((d.stockout_days > 0) & d.base_u.notna(), (d.base_u - d.units).clip(lower=0), 0.0)
    d["lost_r"] = d.lost_u * d.price
    inc = lambda p: d[(d.wk >= p.start.isoformat()) & (d.wk <= p.end.isoformat())]
    dc = inc(cur); dp = inc(prior) if prior else d.iloc[0:0]
    scale = cur.weeks / prior.weeks if prior and prior.weeks else 1
    lost_c, lost_p = float(dc.lost_r.sum()), float(dp.lost_r.sum()) * scale
    lu_c, lu_p = float(dc.lost_u.sum()), float(dp.lost_u.sum()) * scale
    pr = mf.set_index(key)
    pr["lost_revenue"] = dc.groupby(key).lost_r.sum().reindex(pr.index).fillna(0)
    pr["lost_units"] = dc.groupby(key).lost_u.sum().reindex(pr.index).fillna(0)
    pr["delta_pp"] = pr.rate_c - pr.rate_p
    rev = pd.DataFrame({"c": dc.groupby(key).revenue.sum(), "p": dp.groupby(key).revenue.sum() * scale}).reindex(pr.index).fillna(0)
    affected = pr.delta_pp >= 10
    ac, ap = rev.c[affected].sum(), rev.p[affected].sum(); cc, cp = rev.c[~affected].sum(), rev.p[~affected].sum()
    a_chg = (ac / ap - 1) * 100 if ap > 0 else None; c_chg = (cc / cp - 1) * 100 if cp > 0 else None
    onset_wk = None
    if affected.any():
        aff_idx = pr.index[affected]
        wsum = inv.merge(pd.DataFrame(aff_idx.tolist(), columns=key), on=key).groupby("week_start").stockout_days.mean().sort_index()
        pos = C.onset(wsum.values, +1, baseline_n=min(8, max(len(wsum) - 4, 4)), k=1.5, consec=2)
        onset_wk = str(wsum.index[pos])[:10] if pos is not None else None
    pr = pr.reset_index()
    pm = C.product_map(); pr["category"] = pr.product_name.map(lambda p: pm[p]["category"])
    if gb:
        agg = pr.groupby(gb).agg(stockout_days_c=("stockout_days_c", "sum"), pr_weeks_c=("pr_weeks_c", "sum"), stockout_days_p=("stockout_days_p", "sum"), pr_weeks_p=("pr_weeks_p", "sum"),
                                 lost_revenue=("lost_revenue", "sum"), lost_units=("lost_units", "sum")).reset_index()
        agg["rate_c"], agg["rate_p"] = S.mcalc("stockout_rate", agg, "_c"), S.mcalc("stockout_rate", agg, "_p")
        agg["delta_pp"] = agg.rate_c - agg.rate_p
        table, cols = agg.sort_values("lost_revenue", ascending=False), [*gb, "rate_c", "rate_p", "delta_pp", "lost_revenue", "lost_units"]
    else:
        table, cols = pr.sort_values("lost_revenue", ascending=False).head(12), ["product_name", "region", "rate_c", "rate_p", "delta_pp", "lost_revenue", "lost_units"]
    top = table.iloc[0] if len(table) else None
    head = (f"Stockout rate {rc:.1f}% in {cur.label} vs {rp:.1f}% in {prior.label if prior else 'n/a'} ({rc - rp:+.1f} pp). Estimated lost sales {C.money(lost_c)} in {cur.label} vs {C.money(lost_p)} prior "
            f"(incremental {C.money(lost_c - lost_p, True)}).")
    if top is not None and top.lost_revenue > 0:
        head += f" Most affected: {C.label_of(top, gb or key)} ({C.money(top.lost_revenue)} lost)."
    if a_chg is not None and c_chg is not None:
        head += f" Product-regions with materially higher stockouts changed revenue {C.pct(a_chg)} vs {C.pct(c_chg)} for unaffected ones."
    ch = C.chart_bar("Estimated lost sales from stockouts", [{"name": C.label_of(r, gb or key), "value": C.clean(r.lost_revenue, 0)} for _, r in table.head(10).iterrows()],
                     [{"key": "value", "name": "Estimated lost revenue"}], "currency")
    facts = {"rate_cur": C.clean(rc), "rate_prior": C.clean(rp), "rate_delta_pp": C.clean(rc - rp), "lost_revenue_cur": C.clean(lost_c, 0), "lost_revenue_prior_scaled": C.clean(lost_p, 0),
             "incremental_loss_revenue": C.clean(lost_c - lost_p, 0), "incremental_loss_units": C.clean(lu_c - lu_p, 0), "n_affected": int(affected.sum()),
             "affected": [{"product": r.product_name, "region": r.region, "rate_cur": C.clean(r.rate_c), "rate_prior": C.clean(r.rate_p), "lost_revenue": C.clean(r.lost_revenue, 0)} for _, r in pr[affected.values].sort_values("lost_revenue", ascending=False).head(8).iterrows()],
             "affected_revenue_change_pct": C.clean(a_chg), "control_revenue_change_pct": C.clean(c_chg), "onset_week": onset_wk,
             "affected_scope": {"regions": sorted(pr[affected.values].region.unique().tolist()), "products": sorted(pr[affected.values].product_name.unique().tolist())},
             "current_period": cur.to_dict(), "prior_period": prior.to_dict() if prior else None}
    return C.result(head, C.rows(table.head(20), cols), ch, facts,
                    ["Lost sales = expected units (historical share of same-week units in regions without stockouts) minus actual, on stockout weeks; an estimate, not a measured loss.", "Availability is measured at product-region-week level."])


# =============================================================== inventory optimisation
def inventory_optimization(ctx, service_level=0.95, lead_time_weeks=2, max_weeks_cover=6, filters=None, limit=15):
    if not 0.5 <= service_level < 0.999:
        raise ToolError("service_level must be between 0.5 and 0.999.")
    f = C.norm_filters(filters); inv_f = {k: v for k, v in f.items() if k in S.INV_DIMS}; ao = C.as_of(); s = ao - 25 * W
    sales = C.fetch(ctx, "sales", ["week_start", "product_name", "region"], inv_f, s, ao)
    inv = C.fetch(ctx, "inventory", ["week_start", "product_name", "region"], inv_f, s, ao)
    ctx.periods.append(C.Period(s, ao, "last 26 weeks", "weeks"))
    d = sales.merge(inv[["week_start", "product_name", "region", "stockout_days", "stock_units"]], on=["week_start", "product_name", "region"], how="left").fillna({"stockout_days": 0})
    z = NormalDist().inv_cdf(service_level); L = float(lead_time_weeks); out = []
    for (p, r), g in d.groupby(["product_name", "region"]):
        ok = g[g.stockout_days == 0]
        if len(ok) < 8:
            continue
        mu, sd = ok.units.mean(), ok.units.std(ddof=1)
        last = g.sort_values("week_start").iloc[-1]; stock = float(last.stock_units)
        ss = z * sd * np.sqrt(L); rop = mu * L + ss; oup = mu * (L + 1) + ss
        price = g.revenue.sum() / max(g.units.sum(), 1)
        if stock < rop:
            action, qty = "Replenish", oup - stock
        elif stock > mu * max_weeks_cover:
            action, qty = "Reduce / hold orders", stock - mu * max_weeks_cover
        else:
            action, qty = "Hold", 0.0
        out.append({"product": p, "region": r, "avg_weekly_demand": mu, "demand_sd": sd, "safety_stock": ss, "reorder_point": rop, "order_up_to": oup, "current_stock": stock,
                    "weeks_cover": stock / mu if mu else None, "action": action, "recommended_units": qty, "revenue_at_risk": max(0.0, rop - stock) * price})
    if not out:
        raise ToolError("Not enough non-stockout history to size inventory for this scope.")
    df = pd.DataFrame(out).sort_values("revenue_at_risk", ascending=False)
    n_rep, n_red = int((df.action == "Replenish").sum()), int((df.action == "Reduce / hold orders").sum())
    t = df.iloc[0]
    head = (f"Inventory policy at {service_level:.0%} service level and {L:g}-week lead time: {n_rep} product-region(s) below reorder point, {n_red} above {max_weeks_cover:g} weeks of cover. "
            f"Highest exposure: {t['product']} in {t['region']} (stock {t.current_stock:,.0f} vs reorder point {t.reorder_point:,.0f}; ~{C.money(t.revenue_at_risk)} revenue at risk).")
    ch = C.chart_bar("Revenue at risk from below-reorder-point stock", [{"name": f"{r['product']} / {r['region']}", "value": C.clean(r.revenue_at_risk, 0)} for _, r in df.head(10).iterrows()], [{"key": "value", "name": "Revenue at risk"}], "currency")
    return C.result(head, C.rows(df.head(int(limit)), list(df.columns), 1), ch, {"replenish": n_rep, "reduce": n_red, "service_level": service_level, "lead_time_weeks": L, "max_weeks_cover": max_weeks_cover},
                    ["Advisory only: assumes normally distributed weekly demand; excludes MOQ, pack sizes, capacity, supplier lead-time variability and cost of capital.",
                     "Demand statistics exclude stockout weeks to avoid understating demand."])


# =============================================================== forecast
def _design(t):
    w = 2 * np.pi * t / 52
    return np.column_stack([np.ones(len(t)), t / 52, np.sin(w), np.cos(w), np.sin(2 * w), np.cos(2 * w)])


def demand_forecast(ctx, metric="units", horizon_weeks=8, filters=None, group_by=None):
    if metric not in ("units", "revenue"):
        raise ToolError("Forecast metric must be units or revenue.")
    h = max(1, min(int(horizon_weeks), 26)); f = C.norm_filters(filters); gb = [S.norm_dim(g) for g in (group_by or [])][:1]
    ao = C.as_of(); wk = pd.date_range(C.data_min(), ao, freq="7D")
    df = C.fetch(ctx, "sales", ["week_start", *gb], f, C.data_min(), ao); ctx.periods.append(C.Period(C.data_min(), ao, "full history", "range"))
    df["wk"] = pd.to_datetime(df.week_start.astype(str).str[:10])
    groups = [("Total", df.groupby("wk")[metric].sum())] if not gb else [(k, g.groupby("wk")[metric].sum()) for k, g in df.groupby(gb[0])]
    z80, z95 = NormalDist().inv_cdf(.9), 1.96
    res, table = [], []
    for name, s in groups:
        v = s.reindex(wk).ffill().bfill().values.astype(float); n = len(v)
        if n < 60:
            raise ToolError("Need at least 60 weeks of history to forecast.")
        t = np.arange(n); y = np.log(np.clip(v, 1, None)); hold = 8
        b0 = np.linalg.lstsq(_design(t[:-hold]), y[:-hold], rcond=None)[0]
        mape = float(np.mean(np.abs(np.exp(_design(t[-hold:]) @ b0) - v[-hold:]) / v[-hold:]) * 100)
        b = np.linalg.lstsq(_design(t), y, rcond=None)[0]; sd = float(np.std(y - _design(t) @ b, ddof=6))
        ft = np.arange(n, n + h); mu = _design(ft) @ b; sh = sd * np.sqrt(1 + 0.02 * np.arange(1, h + 1))
        rows = [{"group": name, "week": (ao + (i + 1) * W).isoformat(), "forecast": C.clean(np.exp(mu[i]), 0), "lo80": C.clean(np.exp(mu[i] - z80 * sh[i]), 0), "hi80": C.clean(np.exp(mu[i] + z80 * sh[i]), 0),
                 "lo95": C.clean(np.exp(mu[i] - z95 * sh[i]), 0), "hi95": C.clean(np.exp(mu[i] + z95 * sh[i]), 0)} for i in range(h)]
        res.append({"group": name, "holdout_mape_pct": C.clean(mape), "weekly_forecast_avg": C.clean(np.mean([r["forecast"] for r in rows]), 0), "last_8w_avg": C.clean(v[-8:].mean(), 0), "history": v[-26:], "rows": rows})
        table += rows
    main = res[0]
    data = [{"name": (ao - (25 - i) * W).isoformat(), "actual": C.clean(x, 0)} for i, x in enumerate(main["history"])] + \
           [{"name": r["week"], "forecast": r["forecast"], "lo": r["lo80"], "hi": r["hi80"]} for r in main["rows"]]
    chg = (main["weekly_forecast_avg"] / main["last_8w_avg"] - 1) * 100 if main["last_8w_avg"] else 0
    head = (f"{metric.title()} forecast ({main['group']}) next {h} weeks: ~{C.fnum(main['weekly_forecast_avg'])} per week ({C.pct(chg)} vs last 8 weeks), "
            f"80% interval {C.fnum(main['rows'][0]['lo80'])}–{C.fnum(main['rows'][0]['hi80'])} in week 1. Holdout MAPE {main['holdout_mape_pct']}%.")
    ch = C.chart_line(f"{metric.title()} forecast — {main['group']}", data, [{"key": "actual", "name": "Actual"}, {"key": "forecast", "name": "Forecast"}], "count" if metric == "units" else "currency", band={"lo": "lo", "hi": "hi", "label": "80% interval"})
    return C.result(head, table, ch, {"model": "log-linear trend + annual Fourier seasonality (2 harmonics)", "training_weeks": len(wk), "horizon_weeks": h, "holdout_mape_pct": main["holdout_mape_pct"],
                                    "groups": [{k: v for k, v in r.items() if k not in ("history", "rows")} for r in res]},
                    ["Model does not include promotions, price changes or stockouts; history during stockouts understates true demand.", "Intervals widen with horizon and assume stable seasonality."])


# =============================================================== data quality & freshness
def run_dq_checks():
    sales = fetch_df("SELECT week_start, product_name, region, channel, segment, units, revenue, promo_flag, discount_pct FROM fact_sales")
    sales["wk"] = sales.week_start.astype(str).str[:10]
    weeks = sorted(sales.wk.unique()); rows = []
    mi = pd.MultiIndex.from_product([weeks, sorted(sales.product_name.unique()), sorted(sales.region.unique()), sorted(sales.channel.unique())], names=["wk", "product_name", "region", "channel"])
    nseg = sales.segment.nunique()
    cnt = sales.groupby(["wk", "product_name", "region", "channel"]).size().reindex(mi, fill_value=0)
    miss = (nseg - cnt)[cnt < nseg].reset_index(name="missing")
    for (p, r, c), g in miss.groupby(["product_name", "region", "channel"]):
        rows.append(("completeness", "medium", "fail", f"{int(g.missing.sum())} expected rows missing for {p} / {r} / {c} ({len(g)} week(s)).", {"product_name": p, "region": r, "channel": c}, g.wk.min(), g.wk.max(), int(g.missing.sum()), "fact_sales"))
    nd = sales[(sales.promo_flag == 1) & sales.discount_pct.isna()]
    if len(nd):
        rows.append(("null_discount", "low", "fail", f"{len(nd)} promoted rows have no discount depth recorded (revenue is intact; discount-depth metrics are understated).",
                     {"product_name": ", ".join(sorted(nd.product_name.unique()))}, nd.wk.min(), nd.wk.max(), len(nd), "fact_sales"))
    neg = int(((sales.units < 0) | (sales.revenue < 0)).sum())
    rows.append(("negative_values", "high" if neg else "info", "fail" if neg else "pass", f"{neg} rows with negative units/revenue." if neg else "No negative units or revenue.", {}, None, None, neg, "fact_sales"))
    dup = int(sales.duplicated(["wk", "product_name", "region", "channel", "segment"]).sum())
    rows.append(("duplicates", "high" if dup else "info", "fail" if dup else "pass", f"{dup} duplicate grain rows." if dup else "No duplicate grain rows.", {}, None, None, dup, "fact_sales"))
    src = fetch_df("SELECT * FROM data_sources"); nowu = datetime.now(timezone.utc)
    for r in src.itertuples():
        age = (nowu - datetime.fromisoformat(r.last_refreshed)).total_seconds() / 3600
        stale = age > r.cadence_hours
        rows.append(("freshness", "medium" if stale else "info", "fail" if stale else "pass",
                     f"{r.source_name} last refreshed {age:.0f}h ago (expected every {r.cadence_hours}h)." if stale else f"{r.source_name} refreshed {age:.0f}h ago (within {r.cadence_hours}h cadence).", {}, None, None, 0, r.table_name))
    df = pd.DataFrame(rows, columns=["check_name", "severity", "status", "detail", "entity", "week_from", "week_to", "affected_rows", "table_name"])
    import json
    df["entity"] = df.entity.map(json.dumps)
    df["checked_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    df.to_sql("dq_results", engine(), if_exists="replace", index=False)
    return int((df.status == "fail").sum())


def freshness_info(ctx):
    src = fetch_df("SELECT * FROM data_sources"); nowu = datetime.now(timezone.utc); out = []
    for r in src.itertuples():
        if r.table_name in ctx.tables or not ctx.tables:
            age = (nowu - datetime.fromisoformat(r.last_refreshed)).total_seconds() / 3600
            out.append({"source": r.source_name, "table": r.table_name, "system": r.system, "last_refreshed": r.last_refreshed, "age_hours": round(age, 1), "cadence_hours": int(r.cadence_hours), "stale": bool(age > r.cadence_hours)})
    return out


def dq_relevant(ctx):
    import json
    try:
        dq = fetch_df("SELECT * FROM dq_results WHERE status = 'fail'")
    except Exception:
        return []
    out = []
    for r in dq.itertuples():
        if r.table_name not in ctx.tables:
            continue
        if r.check_name != "freshness" and r.week_from and ctx.periods:
            a, b = str(r.week_from)[:10], str(r.week_to)[:10]
            if not any(a <= p.end.isoformat() and b >= p.start.isoformat() for p in ctx.periods):
                continue
        ent = json.loads(r.entity or "{}")
        if any(k in ctx.filters and not any(x.strip() in ctx.filters[k] for x in str(v).split(",")) for k, v in ent.items()):
            continue
        out.append({"check": r.check_name, "severity": r.severity, "detail": r.detail, "table": r.table_name})
    return out


def data_quality_check(ctx, period=None, filters=None):
    f = C.norm_filters(filters)
    cur = C.resolve_period(period or "last_12_weeks")
    ctx.tables.update(["fact_sales", "fact_inventory", "fact_promotions", "fact_competitor", "fact_cohorts"]); ctx.periods.append(cur); C.apply_scope(ctx, "sales", f)
    issues = dq_relevant(ctx); fr = freshness_info(ctx)
    stale = [x for x in fr if x["stale"]]
    head = (f"{len(issues)} data-quality finding(s) relevant to {cur.label}: " + "; ".join(i["detail"] for i in issues[:3]) if issues else f"No open data-quality findings overlap {cur.label}.") + \
           (f" Stale feeds: {', '.join(x['source'] for x in stale)}." if stale else " All feeds are within cadence.")
    return C.result(head, issues, None, {"issues": issues, "freshness": fr, "data_through": (C.as_of() + timedelta(days=6)).isoformat()})
