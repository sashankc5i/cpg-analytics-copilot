"""Institutional memory (MEM-001..005) + outcome monitoring (MEM-004, DEC-003)."""
import math
import re
from collections import Counter
from datetime import date, timedelta

import numpy as np

from .analytics import core as C
from .analytics import performance as P
from .db import jd, jl, now, q, q1, uid, x
from .investigation import get as get_inv

STOP = set("the a an of in on to and or for with by from at is was were as it this that vs".split())


def _tok(t):
    return [w for w in re.findall(r"[a-z][a-z&\-]+", t.lower()) if w not in STOP and len(w) > 2]


def _tfidf(docs, query):
    toks = [_tok(d) for d in docs]; qt = _tok(query); n = len(docs) + 1
    df = Counter(w for t in toks + [qt] for w in set(t))
    idf = lambda w: math.log(n / df[w]) + 1
    vec = lambda t: {w: c * idf(w) for w, c in Counter(t).items()}
    qv = vec(qt); qn = math.sqrt(sum(v * v for v in qv.values())) or 1
    out = []
    for t in toks:
        v = vec(t); vn = math.sqrt(sum(a * a for a in v.values())) or 1
        out.append(sum(qv[w] * v[w] for w in qv if w in v) / (qn * vn))
    return out


def _jac(a, b):
    a, b = set(a), set(b)
    return len(a & b) / len(a | b) if a | b else 0.0


def signature(inv):
    hyps = inv["hypotheses"]
    ents = {k: v for k, v in inv["spec"]["filters"].items()}
    for h in hyps:
        if h["category"] == "Localisation" and h["status"] == "supported":
            m = re.match(r"Gap is concentrated in (.+?) \((\w+)", h["statement"])
            if m:
                ents.setdefault({"customer segment": "segment", "product": "product_name"}.get(m.group(2), m.group(2)), [m.group(1)])
    return {"metric": inv["spec"]["metric"], "direction": "down" if (inv["gap"]["delta"] or 0) < 0 else "up", "entities": ents,
            "supported": [h["key"] for h in hyps if h["status"] == "supported" and h["category"] == "Cause"], "contradicted": [h["key"] for h in hyps if h["status"] == "contradicted" and h["category"] == "Cause"],
            "unresolved": [h["key"] for h in hyps if h["status"] == "unresolved" and h["category"] == "Cause"], "gap_pct": inv["gap"]["pct"], "month": date.today().month}


def _text(inv, sig):
    ents = " ".join(" ".join(v) for v in sig["entities"].values())
    return f"{inv['title']} {inv['observation']} {ents} {' '.join(sig['supported'])} " + " ".join(h["statement"] for h in inv["hypotheses"] if h["status"] == "supported")


def find_similar(inv, k=5):
    rows = q("SELECT * FROM issue_memory WHERE investigation_id IS NULL OR investigation_id != ?", (inv["id"],))
    if not rows:
        return []
    sig = signature(inv); txt = _tfidf([r["text"] for r in rows], _text(inv, sig)); res = []
    flat = lambda s: [f"{d}:{v}" for d, vs in s["entities"].items() for v in vs]
    for r, tf in zip(rows, txt):
        rs = jl(r["signature_json"], {})
        seas = 1 - min(abs((date.fromisoformat(r["occurred_on"][:10]).month - sig["month"] + 6) % 12 - 6), 6) / 6
        sim = .4 * tf + .25 * _jac(flat(sig), flat(rs)) + .25 * _jac(sig["supported"], rs.get("supported", [])) + .1 * seas
        if sim >= .12:
            res.append({"id": r["id"], "title": r["title"], "similarity": round(sim, 3), "occurred_on": r["occurred_on"][:10], "root_cause": r["root_cause"], "source": r["source"],
                        "shared": {"entities": sorted(set(flat(sig)) & set(flat(rs))), "supported": sorted(set(sig["supported"]) & set(rs.get("supported", [])))},
                        "differs": {"this_only_supported": sorted(set(sig["supported"]) - set(rs.get("supported", []))), "past_only_supported": sorted(set(rs.get("supported", [])) - set(sig["supported"]))},
                        "hypotheses": {k_: rs.get(k_, []) for k_ in ("supported", "contradicted", "unresolved")}, "outcome": jl(r["outcome_json"]), "investigation_id": r["investigation_id"]})
    return sorted(res, key=lambda r: -r["similarity"])[:k]


def hypothesis_recall(similar):
    t = {}
    for s in similar:
        for st, lst in s["hypotheses"].items():
            for h in lst:
                t.setdefault(h, {"supported": 0, "contradicted": 0, "unresolved": 0})[st] += 1
    return t


def store(inv, user=None):
    sig = signature(inv); sup = [h for h in inv["hypotheses"] if h["status"] == "supported" and h["category"] == "Cause"]
    root = sup[0]["statement"] if sup else "No dominant cause identified"
    x("DELETE FROM issue_memory WHERE investigation_id=?", (inv["id"],))
    x("INSERT INTO issue_memory VALUES(?,?,?,?,?,?,?,?,?,?,?)", (uid("mem_"), inv["id"], inv["title"], jd(sig), _text(inv, sig), jd([{"key": h["key"], "status": h["status"], "explained_pct": h["explained_pct"]} for h in inv["hypotheses"]]),
                                                                 root, jd(None), "investigation", now(), now()))


def search(query, limit=10):
    rows = q("SELECT * FROM issue_memory")
    if not rows:
        return []
    sc = _tfidf([r["title"] + " " + r["text"] for r in rows], query) if query.strip() else [0] * len(rows)
    out = [{"id": r["id"], "title": r["title"], "score": round(s, 3), "occurred_on": r["occurred_on"][:10], "root_cause": r["root_cause"], "source": r["source"], "signature": jl(r["signature_json"]),
            "outcome": jl(r["outcome_json"]), "investigation_id": r["investigation_id"]} for r, s in zip(rows, sc) if s > 0.02 or not query.strip()]
    return sorted(out, key=lambda r: -r["score"])[:limit]


def record_outcome(inv_id, user, action, result, before, after, notes):
    oid = uid("out_")
    x("INSERT INTO outcomes VALUES(?,?,?,?,?,?,?,?,?)", (oid, inv_id, action, result, before, after, notes, user["username"], now()))
    row = q1("SELECT id FROM issue_memory WHERE investigation_id=?", (inv_id,))
    if row:
        x("UPDATE issue_memory SET outcome_json=? WHERE id=?", (jd({"action": action, "result": result, "metric_before": before, "metric_after": after, "notes": notes}), row["id"]))
    return oid


def monitor_outcome(inv, user):
    sp = inv["spec"]; f = C.norm_filters(sp["filters"]); ctx = C.Ctx(scope=user["scope"])
    wk, mat = P.weekly_matrix(ctx, sp["metric"], None, f); v = mat["Total"]; wk = list(wk)
    cur, pri = sp["current"], sp["prior"]
    idx = lambda d: next((i for i, w in enumerate(wk) if w >= d), len(wk) - 1)
    avg = lambda p: float(np.mean(v[idx(p["start"]):idx(p["end"]) + 1]))
    baseline, issue = avg(pri), avg(cur)
    done = [a for a in q("SELECT * FROM actions WHERE investigation_id=? AND status='done' AND completed_at IS NOT NULL ORDER BY completed_at DESC", (inv["id"],))]
    post_start = idx(done[0]["completed_at"][:10]) if done else None
    post = float(np.mean(v[post_start:])) if post_start is not None and post_start < len(v) - 1 else None
    rec = ((post - issue) / (baseline - issue) * 100) if post is not None and abs(baseline - issue) > 1e-9 else None
    data = [{"name": w, "value": C.clean(x_)} for w, x_ in zip(wk[-40:], v[-40:])]
    return {"metric": sp["metric"], "baseline_weekly_avg": C.clean(baseline), "issue_weekly_avg": C.clean(issue), "post_action_weekly_avg": C.clean(post), "recovery_pct": C.clean(rec), "action_completed": done[0]["completed_at"][:10] if done else None,
            "status": "no completed actions yet" if not done else ("recovered" if rec and rec >= 80 else "partially recovered" if rec and rec >= 30 else "not recovered" if rec is not None else "insufficient post-action data"),
            "chart": C.chart_line("Weekly " + sp["metric"] + " (scope of investigation)", data, [{"key": "value", "name": sp["metric"]}], "currency" if sp["metric"] == "revenue" else "count")}


SEEDS = [
    (400, "Beverage revenue dip in South driven by Fizzo stockouts", "Revenue fell sharply in South region beverages Fizzo Cola Fizzo Zero. Stockouts at the South distribution centre after replenishment delays. Price unchanged, competitor flat.",
     {"region": ["South"], "category": ["Beverages"]}, ["STOCKOUT"], ["PRICE", "COMPETITOR"], ["PROMO"], "Replenishment delays at the South DC",
     {"action": "Expedited replenishment and safety-stock reset", "result": "Revenue recovered ~92% within 6 weeks", "notes": "Safety stock policy updated for summer peak."}),
    (330, "Snacks decline in West after national promotion ended", "Snacks revenue declined West region after Crunch Bites promotion ended with post-promo dip and cannibalisation of Crunch Minis.",
     {"region": ["West"], "category": ["Snacks"]}, ["PROMO", "CANNIBAL"], ["STOCKOUT"], [], "Promotion ended; post-promo dip",
     {"action": "Re-timed promo cadence with a lighter follow-up mechanic", "result": "Stabilised in 3 weeks", "notes": "Cannibalisation ratio was ~20%."}),
    (260, "Household detergent volume loss after list price increase", "Sparkle Detergent volume fell in Value segment after 9% list price increase. Household category revenue down, elastic Value shoppers.",
     {"category": ["Household"], "segment": ["Value"]}, ["PRICE"], ["STOCKOUT"], ["COMPETITOR"], "List price increase in price-sensitive Value segment",
     {"action": "Introduced value pack at lower price per unit", "result": "Recovered ~60% of lost volume", "notes": "Premium segment unaffected."}),
    (190, "Personal Care softness during competitor promotion window", "Personal Care revenue soft while competitor promotional intensity and price index shifted. Silk Shampoo and Conditioner affected.",
     {"category": ["Personal Care"]}, ["COMPETITOR"], ["STOCKOUT", "PRICE"], ["SEASON"], "Competitor promotional pressure",
     {"action": "Targeted counter-promotion in supermarkets", "result": "Share loss halted; margin diluted", "notes": "Evidence was correlational."}),
    (150, "E-commerce revenue dip traced to missing data feed", "Apparent e-commerce channel decline Aqua Pure East caused by missing weekly data rows. Data quality completeness issue.",
     {"channel": ["E-commerce"]}, ["DATAQ"], ["STOCKOUT", "PROMO"], [], "Missing rows in the sales feed",
     {"action": "Data steward back-filled missing weeks", "result": "No real business decline", "notes": "Added completeness alert."}),
    (60, "Autumn beverage slowdown mistaken for a problem", "Beverages revenue declined as autumn arrived. Same weeks last year showed the same seasonal decline. No stockout or price change.",
     {"category": ["Beverages"]}, ["SEASON"], ["STOCKOUT", "PRICE", "PROMO"], [], "Normal seasonal pattern",
     {"action": "No action; annotated seasonality in the dashboard", "result": "Resolved by seasonal recovery", "notes": "Seasonality check should run first."}),
]


def seed():
    if q1("SELECT id FROM issue_memory LIMIT 1"):
        return
    for ago, title, text, ents, sup, con, unr, root, out in SEEDS:
        d = (date.today() - timedelta(days=ago)).isoformat()
        sig = {"metric": "revenue", "direction": "down", "entities": ents, "supported": sup, "contradicted": con, "unresolved": unr, "gap_pct": -6, "month": date.fromisoformat(d).month}
        hyps = [{"key": k, "status": "supported"} for k in sup] + [{"key": k, "status": "contradicted"} for k in con] + [{"key": k, "status": "unresolved"} for k in unr]
        x("INSERT INTO issue_memory VALUES(?,?,?,?,?,?,?,?,?,?,?)", (uid("mem_"), None, title, jd(sig), title + " " + text + " " + " ".join(sup), jd(hyps), root, jd(out), "historical (seeded example)", d, now()))
