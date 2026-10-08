"""Investigation engine: plan -> hypotheses -> deterministic evidence -> challenge -> confidence -> summary (INV-*, TRU-*)."""
import json
import logging
import time
from datetime import date, timedelta

import numpy as np

from . import nlu, tools
from . import semantic as S
from .analytics import core as C
from .analytics import performance as P
from .db import jd, jl, now, q, q1, uid, x
from .governance import audit
from .llm import llm
from .logging_setup import log

UNTESTABLE = [
    ("DISTRIBUTION", "Loss of retailer distribution or delisting", "Weighted/numeric distribution by retailer and store"),
    ("SUPPLY", "Upstream supply disruption beyond observed stockouts", "Production schedules, OTIF and logistics disruption data"),
    ("MARKETING", "Reduced marketing / media support", "Media spend, GRPs and digital campaign data"),
    ("EXTERNAL", "External events (weather, holidays, macro shocks)", "External events calendar and weather data"),
]
COVER = {"STOCKOUT": 1, "PROMO": 1, "PRICE": 1, "MIX": 1, "COMPETITOR": .6, "CANNIBAL": .8, "SEASON": .7, "DATAQ": .5, "WHERE_region": 1, "WHERE_channel": 1, "WHERE_segment": 1, "WHERE_product_name": 1}


class Env:
    def __init__(self, user, rid, spec, inv_id):
        self.user, self.rid, self.spec, self.inv_id = user, rid, spec, inv_id
        self.evidence, self.steps, self.cache, self.n = [], [], {}, 0
        self.G = 0.0; self.d = 1; self.cur = self.prior = None; self.metric_onset = None

    def step(self, kind, title, tool=None, args=None, ev=None, detail=None, ms=None):
        self.steps.append({"n": len(self.steps) + 1, "ts": now(), "kind": kind, "title": title, "tool": tool, "args": args, "evidence": ev or [], "detail": detail, "duration_ms": ms})

    def run(self, name, args, title=None):
        k = name + json.dumps(args, sort_keys=True, default=str)
        if k in self.cache:
            return self.cache[k]
        t0 = time.time(); res = tools.execute(name, args, self.user, self.rid)
        if "error" in res:
            self.step("test", title or name, name, args, [], f"Unavailable: {res['error']}", round((time.time() - t0) * 1000))
            self.cache[k] = (None, None, res["error"]); return self.cache[k]
        self.n += 1; label = f"E{self.n}"
        x("INSERT INTO evidence VALUES(?,?,?,?,?,?,?,?,?)", (uid("ev_"), "investigation", self.inv_id, label, None, name, jd(args), jd(res), now()))
        self.evidence.append({"label": label, "tool": name, "headline": res["headline"], "args": args})
        self.step("test", title or name, name, args, [label], res["headline"], round((time.time() - t0) * 1000))
        self.cache[k] = (res, label, None); return self.cache[k]

    def base(self, **extra):
        return {"period": self.spec["period"], "compare_to": self.spec["compare_to"], "filters": self.spec["filters"], **extra}

    def amount(self, rev, units):
        return rev if self.spec["metric"] == "revenue" else units

    def pct(self, amt):
        return (amt / self.G) if self.G else 0.0

    def fmt(self, v, sign=True):
        return C.fmt(self.spec["metric"], v, sign)


def _hyp(key, statement, category, status, amount=None, env=None, strength=0, consistency=.6, rationale="", evidence=None, limits=None, contra=None, data_needed=None):
    pct = (env.pct(amount) if (env and amount is not None) else 0.0)
    return {"key": key, "statement": statement, "category": category, "status": status, "explained_amount": C.clean(amount, 1) if amount is not None else None, "explained_pct": C.clean(pct * 100, 1),
            "criteria": {"materiality": 0, "strength": round(float(strength), 2), "consistency": round(float(consistency), 2), "coverage": COVER.get(key, 0)}, "rationale": rationale,
            "evidence": [e for e in (evidence or []) if e], "limitations": limits or [], "contradictions": contra or [], "data_needed": data_needed}


def _win(effects, p, kinds, key, scale=1.0):
    return sum(e[key] or 0 for e in effects if p["start"] <= e["week"] <= p["end"] and e["kind"] in kinds) * scale


# ------------------------------------------------------------------ tests
def t_stockout(env):
    r, l, err = env.run("stockout_analysis", {**env.base()}, "Test: did stockouts increase in scope?")
    if not r:
        return _hyp("STOCKOUT", "Higher stockouts reduced sales", "Cause", "untestable", rationale=err, data_needed="Inventory availability data")
    f = r["facts"]; amt = -(env.amount(f["incremental_loss_revenue"], f["incremental_loss_units"]) or 0)
    pct = env.pct(amt); contra = []; cons = .6
    a, c = f["affected_revenue_change_pct"], f["control_revenue_change_pct"]
    if a is not None and c is not None:
        if a - c > -3 and env.d < 0:
            contra.append({"text": f"Product-regions with higher stockouts changed {C.pct(a)} vs {C.pct(c)} for unaffected ones — no clear differential.", "evidence": [l]}); cons = .3
        elif a - c <= -3 and env.d < 0:
            cons = .9
    on = f.get("onset_week")
    if on and env.metric_onset and date.fromisoformat(on) > date.fromisoformat(env.metric_onset) + timedelta(days=14):
        contra.append({"text": f"Stockouts began ({on}) more than 2 weeks after the metric started falling ({env.metric_onset}).", "evidence": [l]}); cons = max(.2, cons - .3)
    if f["rate_delta_pp"] <= 0.5 and env.d < 0:
        st, why = "contradicted", f"Stockout rate did not rise ({f['rate_prior']:.1f}% → {f['rate_cur']:.1f}%)."
    elif f["rate_delta_pp"] >= 2 and pct >= .10:
        st, why = "supported", f"Stockout rate rose {f['rate_prior']:.1f}% → {f['rate_cur']:.1f}%; estimated incremental lost sales {C.money(f['incremental_loss_revenue'])}, concentrated in {', '.join(f['affected_scope']['products'][:3])} / {', '.join(f['affected_scope']['regions'][:3])}."
    else:
        st, why = "unresolved", f"Stockouts moved {f['rate_delta_pp']:+.1f} pp; estimated impact {C.money(f['incremental_loss_revenue'], True)} is small relative to the gap."
    return _hyp("STOCKOUT", "Higher stockouts reduced sales in affected product-regions", "Cause", st, amt, env, min(1, max(f["rate_delta_pp"], 0) / 10), cons, why, [l], r["limitations"][:1], contra)


def t_promo(env):
    r, l, err = env.run("promotion_analysis", {"analysis": "impact", **env.base()}, "Test: did promotional support change?")
    if not r:
        return _hyp("PROMO", "Reduced promotional support", "Cause", "untestable", rationale=err)
    f = r["facts"]; k = "revenue" if env.spec["metric"] == "revenue" else "units"
    eff = f["weekly_effects"]; cp, pp = f["current_period"], f["prior_period"]; sc = cp["weeks"] / pp["weeks"] if pp["weeks"] else 1
    amt = _win(eff, cp, ("lift", "post_dip", "cannibalisation"), k) - _win(eff, pp, ("lift", "post_dip", "cannibalisation"), k, sc)
    pct = env.pct(amt)
    if not f["n_events"]:
        return _hyp("PROMO", "Reduced promotional support", "Cause", "contradicted", 0, env, 0, .6, "No promotions overlapped either window.", [l])
    ended = [e for e in f["events"] if e["end"] < cp["start"]]
    if pct >= .10:
        st, why = "supported", f"Promotional effect fell by {env.fmt(abs(amt), False)} between windows ({', '.join(e['promo_id'] + ' ' + e['product'] for e in ended[:2]) or 'fewer promoted weeks'} ended; post-promo dip {C.money(f['post_dip_cur'], True)}). Promo share {f['promo_share_prior']:.1f}% → {f['promo_share_cur']:.1f}%."
    elif pct <= -.05:
        st, why = "contradicted", f"Promotional effect rose between windows ({env.fmt(amt)}), the opposite direction of the gap."
    else:
        st, why = "unresolved", f"Promotional effect changed by {env.fmt(amt)}, small relative to the gap."
    return _hyp("PROMO", "Reduced promotional support (promotions ended, post-promo dip)", "Cause", st, amt, env, min(1, abs(pct)), .7, why, [l], r["limitations"][:1])


def t_price(env):
    r, l, err = env.run("price_volume_mix", env.base(), "Test: did list prices change and did volume react?")
    if not r:
        return _hyp("PRICE", "Price changes depressed volume", "Cause", "untestable", rationale=err)
    f = r["facts"]; rep = f["repriced"]
    if not rep:
        return _hyp("PRICE", "Price changes depressed volume", "Cause", "contradicted", 0, env, 0, .6, "No product had a list-price change of 3% or more between the windows.", [l])
    g = f["units_control_pct"] or 0; ex_u = sum((p["units_current"] - p["units_prior"] * (1 + g / 100)) for p in rep)
    ex_r = sum((p["units_current"] - p["units_prior"] * (1 + g / 100)) * (p["price_prior"] or 0) for p in rep)
    gain = sum(row["list_price_effect"] or 0 for row in r["rows"] if row["product_name"] in {p["product"] for p in rep})
    amt = env.amount(ex_r + gain, ex_u); pct = env.pct(amt)
    names = ", ".join(f"{p['product']} ({C.pct(p['list_price_change_pct'])} price, {C.pct(p['units_change_pct'])} units)" for p in rep[:2])
    if ex_u < 0 and pct >= .05:
        st, why = "supported", f"Repriced: {names}. Units fell {abs(ex_u):,.0f} more than the {C.pct(g)} control trend; net price/volume effect {env.fmt(amt)}."
    elif ex_u >= -0.02 * sum(p["units_prior"] for p in rep):
        st, why = "contradicted", f"Repriced: {names}, but volume held relative to the {C.pct(g)} control trend."
    else:
        st, why = "unresolved", f"Repriced: {names}; net effect {env.fmt(amt)} is small versus the gap."
    return _hyp("PRICE", "List-price increases depressed volume in repriced products", "Cause", st, amt, env, min(1, abs(pct) * 2), .7, why, [l], r["limitations"][:1])


def t_mix(env):
    if env.spec["metric"] != "revenue":
        return _hyp("MIX", "Mix shift toward lower-priced products", "Cause", "untestable", rationale="Mix is defined for revenue only.")
    r, l, err = env.run("price_volume_mix", env.base(), "Test: mix shift")
    if not r:
        return _hyp("MIX", "Mix shift toward lower-priced products", "Cause", "untestable", rationale=err)
    amt = r["facts"]["mix"]; pct = env.pct(amt)
    st = "supported" if pct >= .2 else "contradicted" if pct <= -.05 else "unresolved"
    return _hyp("MIX", "Mix shift toward lower-priced products reduced revenue", "Cause", st, amt, env, min(1, abs(pct)), .6, f"Mix effect {C.money(amt, True)} ({pct * 100:.0f}% of the gap).", [l])


def t_where(env, dim, label):
    r, l, err = env.run("driver_decomposition", {"period": env.spec["period"], "compare_to": env.spec["compare_to"], "metric": env.spec["metric"], "filters": env.spec["filters"]}, "Locate the gap by dimension")
    key = "WHERE_" + dim
    if not r:
        return _hyp(key, label, "Localisation", "untestable", rationale=err)
    c = r["facts"]["concentration"][dim]; top = next((t for t in r["facts"]["top_drivers"] if t["dimension"] == dim and t["member"] == c["top_member"]), {})
    sh = c["top_share_of_gap"] or 0; dis = top.get("disproportion") or 0
    st = "supported" if abs(sh) >= 40 and dis >= 1.5 else "contradicted" if abs(sh) < 20 else "unresolved"
    return _hyp(key, label.format(m=c["top_member"]), "Localisation", st, c["top_delta"], env, min(1, abs(sh) / 100), .7,
                f"{c['top_member']} contributes {sh:.0f}% of the gap ({dis:.1f}x its revenue share).", [l])


def t_competitor(env):
    cats = env.spec["filters"].get("category")
    r, l, err = env.run("competitor_signals", {"period": env.spec["period"], "compare_to": env.spec["compare_to"], **({"category": cats[0]} if cats and len(cats) == 1 else {})}, "Test: competitor activity")
    if not r:
        return _hyp("COMPETITOR", "Competitor activity pulled share", "Cause", "untestable", rationale=err, data_needed="Governed competitor price/promo feed for these categories")
    cs = r["facts"]["categories"]; k = "est_revenue_effect"
    if env.spec["metric"] == "revenue":
        amt = sum(c[k] or 0 for c in cs)
    else:
        amt = float(np.mean([c["est_units_effect_pct"] or 0 for c in cs])) / 100 * (r_cur(env) or 0)
    big = max(cs, key=lambda c: abs(c["promo_delta"] or 0)); pct = env.pct(amt)
    if (big["promo_delta"] or 0) >= .1 and (big["corr_with_our_units"] or 0) <= -.25 and pct >= .05:
        st = "supported"
    elif (big["promo_delta"] or 0) >= .1:
        st = "unresolved"
    else:
        st = "contradicted"
    why = (f"Competitor promo intensity in {big['category']} moved {big['prior_promo_intensity']} → {big['competitor_promo_intensity']}; correlation with our units {big['corr_with_our_units']}; implied effect {env.fmt(amt)}."
           + (f" No external data for {', '.join(r['facts']['missing_categories'])}." if r["facts"]["missing_categories"] else ""))
    return _hyp("COMPETITOR", "Competitor promotional activity pulled demand", "Cause", st, amt, env, min(1, abs(big["corr_with_our_units"] or 0)), .5, why, [l], r["limitations"][:1])


def r_cur(env):
    return getattr(env, "gap_cur", None)


def t_cannibal(env):
    r, l, err = env.run("promotion_analysis", {"analysis": "cannibalization", **env.base()}, "Test: cannibalisation by promoted products")
    if not r or not r["facts"]["n_events"]:
        return _hyp("CANNIBAL", "Promoted products cannibalised related products", "Cause", "contradicted", 0, env, 0, .6, "No promotions with tracked substitutes in the windows.", [l])
    f = r["facts"]; k = "revenue" if env.spec["metric"] == "revenue" else "units"; eff = f["weekly_effects"]; cp, pp = f["current_period"], f["prior_period"]
    sc = cp["weeks"] / pp["weeks"] if pp["weeks"] else 1
    amt = _win(eff, cp, ("cannibalisation",), k) - _win(eff, pp, ("cannibalisation",), k, sc); pct = env.pct(amt)
    st = "supported" if pct >= .10 else "unresolved" if pct > 0.02 else "contradicted"
    return _hyp("CANNIBAL", "Promoted products cannibalised related products", "Cause", st, amt, env, min(1, abs(pct)), .6, f"Substitute losses changed by {env.fmt(amt)} between windows.", [l], r["limitations"][-1:])


def t_season(env):
    cp, pp = env.cur, env.prior
    s, e = date.fromisoformat(cp["start"]) - timedelta(days=364), date.fromisoformat(cp["end"]) - timedelta(days=364)
    if s - timedelta(days=(e - s).days + 1) < C.data_min():
        return _hyp("SEASON", "Normal seasonal pattern", "Cause", "untestable", rationale="Not enough prior-year history.", data_needed="At least two years of history")
    r, l, err = env.run("compare_periods", {"metric": env.spec["metric"], "period": f"{s}..{e}", "compare_to": "prior_period", "filters": env.spec["filters"]}, "Test: same weeks last year (seasonality)")
    if not r:
        return _hyp("SEASON", "Normal seasonal pattern", "Cause", "untestable", rationale=err)
    sp = r["facts"]["pct"] or 0; amt = sp / 100 * env.spec_prior; pct = env.pct(amt)
    st = "supported" if pct >= .3 else "contradicted" if (pct < 0.05 or abs(sp) < 1) else "unresolved"
    return _hyp("SEASON", "Normal seasonal pattern explains the movement", "Cause", st, amt, env, min(1, abs(pct)), .6, f"The same weeks last year moved {C.pct(sp)} (seasonal expectation {env.fmt(amt)} vs actual gap {env.fmt(env.G)}).", [l])


def t_dq(env):
    r, l, err = env.run("data_quality_check", {"period": env.spec["period"], "filters": env.spec["filters"]}, "Test: data-quality artefacts")
    if not r:
        return _hyp("DATAQ", "Missing or stale data distorts the comparison", "Cause", "untestable", rationale=err)
    comp = [i for i in r["facts"]["issues"] if i["check"] == "completeness"]
    st = "unresolved" if comp else "contradicted"
    why = ("Completeness issues overlap the window: " + "; ".join(i["detail"] for i in comp[:2]) + " (could understate current values).") if comp else "No completeness issues overlap the comparison windows."
    return _hyp("DATAQ", "Missing or stale data distorts the comparison", "Cause", st, 0, env, .2 if comp else 0, .6, why, [l])


# ------------------------------------------------------------------ main
def _score(h):
    c = h["criteria"]; pct = max(0, min(1, (h["explained_pct"] or 0) / 100)); c["materiality"] = round(pct, 2)
    h["score"] = round(.45 * pct + .25 * c["strength"] + .20 * c["consistency"] + .10 * c["coverage"], 3)
    if h["status"] == "supported" and h["score"] < .35:
        h["status"] = "unresolved"
    if h["status"] == "untestable":
        h["score"] = 0
    return h


def _extra_hyps(observation):
    out = list(UNTESTABLE[:4])
    if llm.available:
        try:
            j = llm.json("You help CPG analysts. Propose up to 2 additional plausible business explanations NOT answerable from sales, inventory, promotion, price or competitor data. "
                         'Format: {"hypotheses":[{"statement":"...","data_needed":"..."}]}', observation, "hypothesis_generation", 400)
            for i, h in enumerate(j.get("hypotheses", [])[:2]):
                out.append((f"LLM{i + 1}", str(h["statement"])[:140], str(h.get("data_needed", "Additional data"))[:140]))
        except Exception as e:
            log("investigation", logging.INFO, "llm hypothesis generation skipped", error=str(e)[:120])
    return out


def _narrative(inv):
    s = inv["summary"]
    if llm.available:
        try:
            facts = {"headline": s["headline"], "gap": inv["gap"], "claims": [{"id": c["id"], "text": c["text"], "evidence": c["evidence"]} for c in s["claims"]],
                     "confidence": inv["confidence"]["level"], "unexplained_pct": s["unexplained_pct"], "missing": [m["text"] for m in inv["challenge"]["missing_evidence"][:3]]}
            m = llm.chat([{"role": "system", "content": "You write crisp executive investigation summaries for CPG leaders. Use ONLY the facts given; never invent numbers. Cite evidence labels like [E3]. 90-140 words. State confidence and the main caveat. No headings."},
                          {"role": "user", "content": json.dumps(facts)}], purpose="investigation_summary", max_tokens=380)
            if m.content:
                return m.content.strip()
        except Exception as e:
            log("investigation", logging.INFO, "llm narrative skipped", error=str(e)[:120])
    return f"{s['conclusion']}\n\n" + "\n".join(f"- {c['text']} " + " ".join(f"[{e}]" for e in c["evidence"]) for c in s["claims"] if c["kind"] == "finding")


def _recs(env, causes):
    recs = []
    for h in causes:
        if h["status"] != "supported":
            continue
        k, ev = h["key"], h["evidence"]
        if k == "STOCKOUT":
            recs.append({"action": "Expedite replenishment and review safety stock for the most-affected product-regions; run inventory optimisation for them.", "rationale": h["rationale"], "evidence": ev,
                         "assumptions": ["Stockouts stem from replenishment/supply gaps rather than demand shifts.", "Lost-sales estimate uses a trailing non-stockout baseline."], "expected_impact": f"Up to ~{h['explained_amount'] and env.fmt(abs(h['explained_amount']), False)} recoverable if availability returns to prior levels."})
        elif k == "PROMO":
            recs.append({"action": "Review the promo calendar: decide whether to extend, replace or re-time activity for the ended promotions; check post-promo recovery.", "rationale": h["rationale"], "evidence": ev,
                         "assumptions": ["Baseline demand has not structurally changed.", "Promotions were profitable at the prior depth."], "expected_impact": "Depends on promo ROI; see promotion lift evidence."})
        elif k == "PRICE":
            recs.append({"action": "Test a targeted price/pack-price response (e.g. value-tier pack) for repriced products and monitor elasticity by segment.", "rationale": h["rationale"], "evidence": ev,
                         "assumptions": ["Volume loss is price-driven, not competitor-driven.", "Elasticity estimate is observational."], "expected_impact": "Evaluate with price_optimization before changing prices."})
        elif k == "COMPETITOR":
            recs.append({"action": "Prepare a response plan for competitor promo activity (targeted counter-promotion, retailer negotiations) and keep monitoring.", "rationale": h["rationale"], "evidence": ev,
                         "assumptions": ["Association with competitor intensity is causal."], "expected_impact": "Uncertain — correlational evidence."})
    if not recs:
        recs.append({"action": "No single supported driver: collect the missing evidence listed and re-run the investigation before acting.", "rationale": "Evidence does not support a dominant cause.", "evidence": [], "assumptions": [], "expected_impact": "n/a"})
    return recs


def _graph(inv):
    nodes, edges = [{"id": "obs", "type": "observation", "label": inv["title"][:70]}], []
    seen = set()
    for h in inv["hypotheses"]:
        nodes.append({"id": "h:" + h["key"], "type": "hypothesis", "label": h["statement"][:60], "status": h["status"], "score": h.get("score")})
        edges.append({"from": "h:" + h["key"], "to": "obs", "relation": "explains" if h["status"] == "supported" else "tested", "weight": h["explained_pct"]})
        for l in h["evidence"]:
            if l not in seen:
                seen.add(l); ev = next((e for e in inv["evidence"] if e["label"] == l), {})
                nodes.append({"id": "e:" + l, "type": "evidence", "label": f"{l} {ev.get('tool', '')}", "detail": ev.get("headline", "")})
            edges.append({"from": "e:" + l, "to": "h:" + h["key"], "relation": "supports" if h["status"] == "supported" else "contradicts" if h["status"] == "contradicted" else "informs"})
        for c in h["contradictions"]:
            for l in c.get("evidence", []):
                edges.append({"from": "e:" + l, "to": "h:" + h["key"], "relation": "weakens"})
    for c in inv["summary"]["claims"]:
        nodes.append({"id": "c:" + c["id"], "type": "claim", "label": c["text"][:70], "kind": c["kind"]})
        for l in c["evidence"]:
            if "e:" + l in {n["id"] for n in nodes}:
                edges.append({"from": "e:" + l, "to": "c:" + c["id"], "relation": "backs"})
        if c.get("hypothesis"):
            edges.append({"from": "c:" + c["id"], "to": "h:" + c["hypothesis"], "relation": "asserts"})
    return {"nodes": nodes, "edges": edges}


def start(user, observation, spec=None, conversation_id=None, source="user", issue_id=None, request_id="-", priority=None):
    inv_id = uid("inv_"); t_all = time.time()
    parsed = nlu.parse(observation)
    spec = {**{"metric": parsed["metric"] if parsed["metric"] in ("revenue", "units") else "revenue", "period": parsed["period"] or "last_4_weeks", "compare_to": parsed["compare_to"], "filters": parsed["filters"]}, **{k: v for k, v in (spec or {}).items() if v}}
    spec["filters"] = {k: v for k, v in (spec.get("filters") or {}).items()}
    if spec["metric"] not in ("revenue", "units"):
        spec["metric"] = "revenue"
    if spec["compare_to"] in (None, "none"):
        spec["compare_to"] = "prior_period"
    env = Env(user, request_id, spec, inv_id)
    env.step("observe", "Observation captured", detail=observation)
    # --- observation gap
    g, gl, err = env.run("compare_periods", {"metric": spec["metric"], "period": spec["period"], "compare_to": spec["compare_to"], "filters": spec["filters"]}, "Quantify the observed movement")
    if not g:
        raise ValueError(err)
    gf = g["facts"]; env.G, env.d = gf["delta"] or 0.0, (-1 if (gf["delta"] or 0) < 0 else 1); env.cur, env.prior = gf["current_period"], gf["prior_period"]
    env.spec_prior = gf["prior"]; env.gap_cur = gf["current"]
    gap = {"current": gf["current"], "prior": gf["prior"], "delta": gf["delta"], "pct": gf["pct"], "metric": spec["metric"], "current_label": env.cur["label"], "prior_label": env.prior["label"], "evidence": gl}
    # --- timing baseline
    try:
        ctx = C.Ctx(scope=user["scope"]); wk, mat = P.weekly_matrix(ctx, spec["metric"], None, C.norm_filters(spec["filters"]))
        i0 = max(0, list(wk).index(env.prior["start"]) - 8) if env.prior["start"] in list(wk) else 0
        pos = C.onset(mat["Total"][i0:], env.d, baseline_n=8, k=1.0, consec=2)
        env.metric_onset = str(wk[i0 + pos]) if pos is not None else None
        env.step("test", "Timing check: when did the metric start moving?", detail=f"Metric onset week: {env.metric_onset or 'not detected'}")
    except Exception as e:
        log("investigation", logging.INFO, "timing check skipped", error=str(e)[:120])
    # --- hypotheses
    env.step("hypothesize", "Generate testable hypotheses from the governed catalog + untestable candidates")
    tests = [t_stockout, t_promo, t_price, t_mix, t_competitor, t_cannibal, t_season, t_dq,
             lambda e: t_where(e, "region", "Gap is concentrated in {m} (region)"), lambda e: t_where(e, "channel", "Gap is concentrated in {m} (channel)"),
             lambda e: t_where(e, "segment", "Gap is concentrated in {m} (customer segment)"), lambda e: t_where(e, "product_name", "Gap is concentrated in {m} (product)")]
    plan = [{"id": i + 1, "step": s, "tool": t, "question": qn} for i, (s, t, qn) in enumerate([
        ("Quantify the movement", "compare_periods", "How big is the change vs the comparison period?"), ("Locate the gap", "driver_decomposition", "Where is the change concentrated (region/channel/segment/product)?"),
        ("Test availability", "stockout_analysis", "Did stockouts increase where sales fell?"), ("Test promotions", "promotion_analysis", "Did promotional support or cannibalisation change?"),
        ("Test pricing & mix", "price_volume_mix", "Did list prices or mix shift?"), ("Test external factors", "competitor_signals", "Did competitor activity change?"),
        ("Test seasonality", "compare_periods", "Is this a normal seasonal pattern?"), ("Check data reliability", "data_quality_check", "Could data gaps distort the comparison?"),
        ("Challenge the leading explanation", "—", "What contradicts it, what are the alternatives, what evidence is missing?")])]
    hyps = []
    for t in tests:
        try:
            hyps.append(t(env))
        except Exception as e:
            log("investigation", logging.ERROR, "hypothesis test failed", error=repr(e))
    for k, st, need in _extra_hyps(observation):
        hyps.append(_hyp(k, st, "Cause", "untestable", rationale="No governed data source is available to test this.", data_needed=need))
    hyps = [_score(h) for h in hyps]
    causes = sorted([h for h in hyps if h["category"] == "Cause"], key=lambda h: -h["score"])
    for i, h in enumerate(causes):
        h["rank"] = i + 1
    hyps = causes + [h for h in hyps if h["category"] != "Cause"]
    env.step("rank", "Rank hypotheses on materiality, strength, consistency, coverage", detail="; ".join(f"{h['key']}={h['score']}" for h in causes[:5]))
    # --- challenge
    lead = next((h for h in causes if h["status"] == "supported"), None)
    sup = [h for h in causes if h["status"] == "supported"]
    cum = min(1.0, sum((h["explained_pct"] or 0) for h in sup) / 100)
    contr, alts, missing = [], [], []
    if lead:
        contr += [{"hypothesis": lead["key"], **c} for c in lead["contradictions"]]
        if (lead["explained_pct"] or 0) < 60:
            contr.append({"hypothesis": lead["key"], "text": f"{lead['key'].title()} explains only ~{lead['explained_pct']:.0f}% of the gap on its own.", "evidence": lead["evidence"]})
    for h in causes:
        if h is not lead and h["status"] in ("supported", "unresolved") and (h["explained_pct"] or 0) >= 3:
            alts.append({"key": h["key"], "statement": h["statement"], "status": h["status"], "explained_pct": h["explained_pct"], "evidence": h["evidence"]})
    if sum((h["explained_pct"] or 0) for h in sup) > 105:
        alts.append({"key": "OVERLAP", "statement": "Supported explanations overlap (their shares sum above 100%); effects cannot be cleanly separated.", "status": "note", "explained_pct": None, "evidence": []})
    for h in causes:
        if h["status"] == "untestable":
            missing.append({"text": f"{h['statement']} — cannot be tested.", "data_needed": h.get("data_needed") or "n/a", "hypothesis": h["key"]})
    for k, (res, lab, err) in list(env.cache.items()):
        if res and res.get("meta"):
            for dq in res["meta"]["data_quality"]:
                t = f"Data quality: {dq['detail']}"
                if not any(m["text"] == t for m in missing):
                    missing.append({"text": t, "data_needed": "Data steward remediation", "hypothesis": None})
            for w in res["meta"]["warnings"]:
                if "ignore" in w.lower() or "do not apply" in w.lower():
                    if not any(m["text"] == w for m in missing):
                        missing.append({"text": w, "data_needed": "—", "hypothesis": None})
    n_test = len([h for h in causes if h["status"] != "untestable"]); coverage = n_test / max(len(causes), 1)
    factors = [{"label": "Base", "effect": 40, "detail": "Starting confidence"}, {"label": "Share of gap explained by supported causes", "effect": round(40 * cum), "detail": f"{cum * 100:.0f}% (capped at 100%)"},
               {"label": "Hypothesis coverage", "effect": round(10 * coverage), "detail": f"{n_test} of {len(causes)} hypotheses testable"}]
    pen = 8 * len(lead["contradictions"] if lead else [])
    if pen: factors.append({"label": "Contradictions on leading explanation", "effect": -pen, "detail": f"{len(lead['contradictions'])} found"})
    dqn = len([m for m in missing if m["text"].startswith("Data quality")])
    if dqn: factors.append({"label": "Data-quality limitations", "effect": -4 * dqn, "detail": f"{dqn} relevant finding(s)"})
    if not lead: factors.append({"label": "No supported cause", "effect": -15, "detail": "Evidence does not support a dominant driver"})
    score = int(max(5, min(95, sum(f["effect"] for f in factors))))
    conf = {"level": "high" if score >= 70 else "medium" if score >= 45 else "low", "score": score, "factors": factors}
    env.step("challenge", "Search for contradictions, alternatives and missing evidence", detail=f"{len(contr)} contradiction(s), {len(alts)} alternative(s), {len(missing)} missing-evidence item(s)")
    # --- summary / claims
    wh = [h for h in hyps if h["category"] == "Localisation" and h["status"] in ("supported", "unresolved")]
    gtxt = f"{g['headline']}"
    claims = [{"id": "c1", "kind": "finding", "text": gtxt, "evidence": [gl], "hypothesis": None}]
    for h in wh[:2]:
        claims.append({"id": f"c{len(claims) + 1}", "kind": "finding", "text": f"{h['statement']}: {h['rationale']}", "evidence": h["evidence"], "hypothesis": h["key"]})
    for h in sup:
        claims.append({"id": f"c{len(claims) + 1}", "kind": "finding", "text": f"{h['statement']} (~{h['explained_pct']:.0f}% of the gap). {h['rationale']}", "evidence": h["evidence"], "hypothesis": h["key"]})
    for c in contr[:2]:
        claims.append({"id": f"c{len(claims) + 1}", "kind": "caveat", "text": c["text"], "evidence": c.get("evidence", []), "hypothesis": c.get("hypothesis")})
    for m in missing[:2]:
        claims.append({"id": f"c{len(claims) + 1}", "kind": "caveat", "text": m["text"], "evidence": [], "hypothesis": m.get("hypothesis")})
    unexpl = max(0.0, round((1 - cum) * 100)) if env.G else 0
    concl = (f"Most likely explanation: {lead['statement'].lower()} (~{lead['explained_pct']:.0f}% of the gap)" + (f", with {', '.join(h['key'].lower() for h in sup[1:3])} also contributing" if len(sup) > 1 else "") + f". About {unexpl:.0f}% of the movement remains unexplained. Confidence: {conf['level']}."
             if lead else f"No single driver is supported by the available evidence. Confidence: {conf['level']}.")
    pm = gf["pct"]
    scope_txt = ", ".join(f"{', '.join(v)}" for v in spec["filters"].values())
    title = f"{S.METRICS[spec['metric']]['name']} {C.pct(pm)} {env.cur['label']} vs {env.prior['label']}" + (f" — {scope_txt}" if scope_txt else "")
    sev = priority or ("high" if abs(pm or 0) >= 5 else "medium" if abs(pm or 0) >= 2 else "low")
    inv = {"scope": user["scope"], "id": inv_id, "title": title, "observation": observation, "status": "open", "priority": sev, "owner": None, "due_date": None, "source": source, "issue_id": issue_id, "conversation_id": conversation_id,
           "spec": {**spec, "current": env.cur, "prior": env.prior}, "gap": gap, "plan": plan, "hypotheses": hyps, "challenge": {"contradictions": contr, "alternatives": alts, "missing_evidence": missing}, "confidence": conf,
           "evidence": env.evidence, "summary": {"headline": g["headline"], "claims": claims, "conclusion": concl, "unexplained_pct": unexpl, "limitations": [m["text"] for m in missing if m["text"].startswith("Data quality")], "recommendations": _recs(env, causes), "narrative": ""}}
    inv["summary"]["narrative"] = _narrative(inv)
    env.step("conclude", "Compose evidence-backed summary", detail=concl, ms=round((time.time() - t_all) * 1000))
    inv["graph"] = _graph(inv); inv["replay"] = env.steps
    from . import memory
    try:
        inv["similar"] = memory.find_similar(inv)
        inv["recall"] = memory.hypothesis_recall(inv["similar"])
    except Exception as e:
        log("investigation", logging.ERROR, "memory lookup failed", error=repr(e)); inv["similar"], inv["recall"] = [], {}
    x("INSERT INTO investigations VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (inv_id, user["id"], conversation_id, title, observation, "open", sev, None, None, source, issue_id, jd(inv), now(), now(), None))
    audit(user, "investigation.create", {"id": inv_id, "source": source, "evidence": [e["label"] for e in env.evidence], "tools": sorted({e["tool"] for e in env.evidence})})
    log("investigation", logging.INFO, "investigation created", id=inv_id, evidence=len(env.evidence), ms=round((time.time() - t_all) * 1000))
    return get(inv_id)


def get(inv_id):
    r = q1("SELECT * FROM investigations WHERE id=?", (inv_id,))
    if not r:
        return None
    d = jl(r["data_json"], {})
    d.update({k: r[k] for k in ("id", "title", "observation", "status", "priority", "owner", "due_date", "source", "issue_id", "conversation_id", "user_id", "created_at", "updated_at", "concluded_at")})
    return d


def save(inv):
    data = {k: v for k, v in inv.items() if k not in ("id", "title", "observation", "status", "priority", "owner", "due_date", "source", "issue_id", "conversation_id", "user_id", "created_at", "updated_at", "concluded_at")}
    x("UPDATE investigations SET title=?, status=?, priority=?, owner=?, due_date=?, data_json=?, updated_at=?, concluded_at=? WHERE id=?",
      (inv["title"], inv["status"], inv["priority"], inv["owner"], inv["due_date"], jd(data), now(), inv.get("concluded_at"), inv["id"]))
