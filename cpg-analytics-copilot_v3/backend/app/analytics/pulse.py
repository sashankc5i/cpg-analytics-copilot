"""Proactive BI: business health, issue radar, materiality, correlation, timeline (PBI-001..007)."""
import hashlib
from datetime import date, timedelta

import numpy as np
import pandas as pd

from .. import semantic as S
from ..db import fetch_df
from . import core as C
from . import performance as P
from . import ops

W = timedelta(weeks=1)


def business_health_overview(ctx, period="last_4_weeks"):
    cur = C.resolve_period(period); prior = C.shift(cur, "prior_period")
    kpis = []
    for k in ["revenue", "units", "avg_price", "gross_margin_pct", "promo_share", "stockout_rate"]:
        mf, tot = C.compare_table(ctx, k, [], {}, cur, prior)
        kpis.append({"metric": k, "name": S.METRICS[k]["name"], "unit": S.METRICS[k]["unit"], "current": C.clean(tot["cur"]), "prior": C.clean(tot["prior"]), "delta": C.clean(tot["delta"]), "pct": C.clean(tot["pct"]), "hib": S.METRICS[k]["hib"]})
    wk, mat = P.weekly_matrix(ctx, "revenue", None, {})
    spark = [{"name": w, "value": C.clean(v)} for w, v in zip(wk[-26:], mat["Total"][-26:])]
    movers = {}
    for d in ("region", "category"):
        mf, tot = C.compare_table(ctx, "revenue", [d], {}, cur, prior)
        movers[d] = [{"member": r[d], "delta": C.clean(r.delta), "pct": C.clean(r.pct)} for _, r in mf.reindex(mf.delta.abs().sort_values(ascending=False).index).head(4).iterrows()]
    an = P.anomaly_detection(ctx, "revenue", ["region"], None, 8)
    rev = kpis[0]
    head = (f"Business health ({cur.label} vs {prior.label}): revenue {C.money(rev['current'])} ({C.pct(rev['pct'])}); "
            f"largest regional mover {movers['region'][0]['member']} ({C.pct(movers['region'][0]['pct'])}); {len(an['facts']['summary'])} region(s) with revenue anomalies.")
    return C.result(head, kpis, C.chart_line("Weekly revenue (26 weeks)", spark, [{"key": "value", "name": "Revenue"}], "currency"),
                    {"kpis": kpis, "movers": movers, "anomalies": an["facts"]["summary"], "sparkline": spark, "current_period": cur.to_dict(), "prior_period": prior.to_dict()})


# ------------------------------------------------------------------ radar
def _sev(score):
    return "high" if score >= 60 else "medium" if score >= 35 else "low"


def scan_issues(ctx, window_weeks=4):
    ao = C.as_of(); pm = C.product_map()
    wk, tot = P.weekly_matrix(ctx, "revenue", None, {}); total_rev_window = float(tot["Total"][-window_weeks:].sum())
    issues = []

    def add(kind, domain, title, attrs, amount, dev, z, persistence, share, start):
        mag = min(1, abs(amount) / (0.03 * total_rev_window)) if total_rev_window else 0
        issues.append({"kind": kind, "domain": domain, "title": title, "attrs": attrs, "gap_amount": C.clean(amount, 0), "deviation_pct": C.clean(dev), "z": C.clean(z), "persistence_weeks": persistence,
                       "share_of_revenue_pct": C.clean(share * 100), "start_week": start, "mag": mag, "pers": min(1, persistence / 4), "imp": min(1, share / 0.25)})

    # revenue anomalies by dimension & region x category
    combos = [("region", None), ("category", None), ("channel", None), ("product_name", None), ("segment", None)]
    for dim, _ in combos:
        wk, mat = P.weekly_matrix(ctx, "revenue", dim, {})
        for key, v in mat.items():
            r = P.expected_vs_actual(v, window_weeks)
            if not r:
                continue
            amount = float((r["actual"] - r["expected"]).sum()); dev = float(r["dev"].mean() * 100)
            if abs(r["z"].mean()) >= 2 and (dev <= -5 or dev >= 8):
                pers = next((i for i, x in enumerate(r["dev"][::-1]) if not ((x < -.03) if dev < 0 else (x > .03))), len(r["dev"]))
                attr = {dim: [key]}
                if dim == "product_name":
                    attr["category"] = [pm[key]["category"]]
                share = float(v[-window_weeks:].sum() / total_rev_window) if total_rev_window else 0
                add("revenue_" + ("decline" if dev < 0 else "surge"), "sales", f"Revenue {'decline' if dev < 0 else 'surge'}: {key} ({C.pct(dev)} vs seasonal baseline)", attr, amount, dev, float(r["z"].mean()), pers, share,
                    wk[-window_weeks])
    # region x category pairs
    df = C.fetch(ctx, "sales", ["week_start", "region", "category"], {}, C.data_min(), ao)
    for (rg, ct), g in df.groupby(["region", "category"]):
        v = g.set_index(g.week_start.astype(str).str[:10]).revenue.reindex(wk).ffill().bfill().fillna(0).values
        r = P.expected_vs_actual(v, window_weeks)
        if r and abs(r["z"].mean()) >= 2 and r["dev"].mean() * 100 <= -8:
            dev = float(r["dev"].mean() * 100); pers = next((i for i, x in enumerate(r["dev"][::-1]) if not x < -.03), len(r["dev"]))
            add("revenue_decline", "sales", f"Revenue decline: {ct} in {rg} ({C.pct(dev)})", {"region": [rg], "category": [ct]}, float((r["actual"] - r["expected"]).sum()), dev, float(r["z"].mean()), pers, float(v[-window_weeks:].sum() / total_rev_window), wk[-window_weeks])
    # stockouts
    cur = C.Period(ao - (window_weeks - 1) * W, ao, f"last {window_weeks} weeks", "weeks"); prior = C.shift(cur, "prior_period")
    so = ops.stockout_analysis(ctx, f"last_{window_weeks}_weeks", "prior_period", ["region", "category"], {})
    for r in so["rows"]:
        if (r["delta_pp"] or 0) >= 8 and (r["rate_c"] or 0) >= 15:
            add("stockout_spike", "inventory", f"Stockout spike: {r['category']} in {r['region']} ({r['rate_c']:.0f}% of days, +{r['delta_pp']:.0f} pp)", {"region": [r["region"]], "category": [r["category"]]},
                -(r["lost_revenue"] or 0), None, r["delta_pp"] / 5, window_weeks, (r["lost_revenue"] or 0) / max(total_rev_window, 1), cur.start.isoformat())
    # promotions ended / price changes / competitor
    ev = fetch_df("SELECT * FROM fact_promotions")
    for e in ev.itertuples():
        end = date.fromisoformat(e.end_week[:10])
        if cur.start - 5 * W <= end < cur.start + W:
            add("promo_ended", "promotion", f"Promotion ended: {e.product_name} ({e.promo_id}) — loss of promotional volume", {"product_name": [e.product_name], "category": [e.category]}, 0, None, 0, 2, 0.04, e.end_week[:10])
    pr_df = C.fetch(ctx, "sales", ["week_start", "product_name"], {}, ao - 16 * W, ao)
    for p, g in pr_df.groupby("product_name"):
        lp = (g.set_index(g.week_start.astype(str).str[:10]).gross_revenue / g.set_index(g.week_start.astype(str).str[:10]).units).sort_index()
        if len(lp) >= 12 and lp.iloc[-3:].mean() / lp.iloc[:6].mean() - 1 >= .05:
            ch = (lp.iloc[-3:].mean() / lp.iloc[:6].mean() - 1) * 100
            add("price_increase", "pricing", f"List price increase: {p} ({C.pct(ch)})", {"product_name": [p], "category": [pm[p]["category"]]}, 0, ch, 0, 4, 0.05, lp.index[lp.pct_change().abs().fillna(0).values.argmax()])
    comp = fetch_df("SELECT * FROM fact_competitor"); comp["wk"] = comp.week_start.astype(str).str[:10]
    for ct, g in comp.groupby("category"):
        g = g.sort_values("wk"); recent, base = g.promo_intensity.iloc[-3:].mean(), g.promo_intensity.iloc[:-8].mean()
        if recent - base >= .25:
            add("competitor_promo", "market", f"Competitor promotional spike in {ct} ({base:.2f} → {recent:.2f})", {"category": [ct]}, 0, None, 0, 3, 0.05, g.wk.iloc[-6])
    return issues, total_rev_window


def _cluster(issues):
    n = len(issues); parent = list(range(n))
    find = lambda i: i if parent[i] == i else find(parent[i])
    for i in range(n):
        for j in range(i + 1, n):
            a, b = issues[i], issues[j]
            shared = any(set(a["attrs"].get(k, [])) & set(b["attrs"].get(k, [])) for k in ("region", "category", "product_name"))
            near = abs((date.fromisoformat(a["start_week"][:10]) - date.fromisoformat(b["start_week"][:10])).days) <= 28
            if shared and near and (a["domain"] != b["domain"] or a["kind"] == b["kind"] == "revenue_decline"):
                parent[find(i)] = find(j)
    groups = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(issues[i])
    return list(groups.values())


def detect_business_issues(ctx, limit=8, persist=True):
    issues, tot = scan_issues(ctx)
    clusters = []
    for g in _cluster(issues):
        for it in g:
            it["score"] = round(100 * (.4 * it["mag"] + .25 * it["pers"] + .2 * it["imp"]), 1)
        breadth = min(1, (len({i["domain"] for i in g}) - 1) / 3 + (len(g) - 1) * 0.05)
        sales = [i for i in g if i["domain"] == "sales"]
        lead = max(sales or g, key=lambda i: i["mag"])
        score = min(100, round(max(i["score"] for i in g) + 15 * breadth, 1))
        regions = sorted({v for i in g for v in i["attrs"].get("region", [])}); cats = sorted({v for i in g for v in i["attrs"].get("category", [])})
        prods = sorted({v for i in g for v in i["attrs"].get("product_name", [])})
        filt = {}
        if len(regions) == 1: filt["region"] = regions
        if len(cats) == 1: filt["category"] = cats
        if not filt and prods and len(prods) == 1: filt["product_name"] = prods
        domains = sorted({i["domain"] for i in g})
        title = lead["title"] + (f" with concurrent {', '.join(d for d in domains if d != lead['domain'])} signals" if len(domains) > 1 else "")
        cid = "iss_" + hashlib.md5((lead["kind"] + str(sorted(filt.items())) + lead["start_week"]).encode()).hexdigest()[:8]
        clusters.append({"id": cid, "title": title, "score": score, "severity": _sev(score), "domains": domains, "n_signals": len(g), "start_week": min(i["start_week"] for i in g),
                         "signals": [{k: v for k, v in i.items() if k not in ("mag", "pers", "imp")} for i in sorted(g, key=lambda i: -i["score"])],
                         "components": {"magnitude": round(lead["mag"], 2), "persistence": round(lead["pers"], 2), "importance": round(lead["imp"], 2), "breadth": round(breadth, 2)},
                         "spec": {"metric": "revenue", "period": "last_4_weeks", "compare_to": "prior_period", "filters": filt}})
    clusters.sort(key=lambda c: -c["score"])
    return C.result(f"{len(clusters)} business issue(s) detected; top: {clusters[0]['title']} (materiality {clusters[0]['score']})." if clusters else "No material business issues detected.",
                    [{"id": c["id"], "title": c["title"], "score": c["score"], "severity": c["severity"], "domains": ", ".join(c["domains"]), "signals": c["n_signals"]} for c in clusters[:limit]], None,
                    {"issues": clusters[:int(limit)], "scoring": "100 × (0.4·magnitude + 0.25·persistence + 0.2·importance) + breadth bonus (up to 15)"},
                    ["Materiality = magnitude vs 3% of window revenue, persistence (consecutive weeks), importance (revenue share) and breadth (concurrent domains)."])


# ------------------------------------------------------------------ timeline
def business_timeline(ctx, metric="revenue", period="last_26_weeks", filters=None):
    m = S.metric(metric); cur = C.resolve_period(period); f = C.norm_filters(filters); ctx.periods.append(cur)
    df = C.fetch(ctx, m["source"], ["week_start"], f, cur.start, cur.end); df["v"] = S.mcalc(metric, df)
    series = [{"name": str(r.week_start)[:10], "value": C.clean(r.v)} for r in df.sort_values("week_start").itertuples()]
    ev = []
    pr = fetch_df("SELECT * FROM fact_promotions"); ctx.tables.add("fact_promotions")
    for e in pr.itertuples():
        if e.end_week[:10] >= cur.start.isoformat() and e.start_week[:10] <= cur.end.isoformat() and (not f.get("product_name") or e.product_name in f["product_name"]) and (not f.get("category") or e.category in f["category"]):
            ev.append({"date": e.start_week[:10], "kind": "promotion", "label": f"{e.promo_id} start: {e.product_name} {e.discount_pct * 100:.0f}% off ({e.region}/{e.channel})"})
            ev.append({"date": e.end_week[:10], "kind": "promotion", "label": f"{e.promo_id} last week"})
    inv = C.fetch(ctx, "inventory", ["week_start", "product_name", "region"], {k: v for k, v in f.items() if k in S.INV_DIMS}, cur.start, cur.end)
    inv = inv[inv.stockout_days >= 3]
    for (p, r), g in inv.groupby(["product_name", "region"]):
        if len(g) >= 2:
            ev.append({"date": str(g.week_start.min())[:10], "kind": "stockout", "label": f"Stockouts begin: {p} in {r} ({len(g)} wks ≥3 days)"})
    pdf = C.fetch(ctx, "sales", ["week_start", "product_name"], f, cur.start, cur.end)
    for p, g in pdf.groupby("product_name"):
        lp = (g.gross_revenue / g.units.replace(0, np.nan)).values; w = g.week_start.astype(str).str[:10].values
        ch = np.abs(np.diff(lp) / lp[:-1]) if len(lp) > 2 else []
        for i, c in enumerate(ch):
            if c >= .05:
                ev.append({"date": w[i + 1], "kind": "price", "label": f"List price change: {p} ({(lp[i + 1] / lp[i] - 1) * 100:+.0f}%)"})
    comp = fetch_df("SELECT * FROM fact_competitor"); comp["wk"] = comp.week_start.astype(str).str[:10]
    for ct, g in comp[(comp.wk >= cur.start.isoformat()) & (comp.wk <= cur.end.isoformat())].groupby("category"):
        g = g.sort_values("wk"); hot = g[g.promo_intensity >= .6]
        if len(hot) and (not f.get("category") or ct in f["category"]):
            ev.append({"date": hot.wk.iloc[0], "kind": "competitor", "label": f"Competitor promo spike in {ct}"})
    ev.sort(key=lambda e: e["date"])
    head = f"{len(ev)} business event(s) between {cur.start} and {cur.end} plotted against {m['name']}: " + "; ".join(f"{e['date']} {e['label']}" for e in ev[:3]) + ("…" if len(ev) > 3 else ".")
    return C.result(head, ev, {"type": "timeline", "title": f"{m['name']} with business events", "unit": m["unit"], "data": series, "events": ev}, {"events": ev, "period": cur.to_dict()})
