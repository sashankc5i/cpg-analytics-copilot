"""Conversation orchestration: LLM interprets -> governed tools calculate -> evidence-cited answer."""
import json
import logging
import re

from . import investigation, memory, nlu, tools
from . import semantic as S
from .analytics import core as C
from .db import jd, jl, now, q, q1, uid, x
from .governance import audit
from .llm import LLMUnavailable, llm
from .logging_setup import log, request_id_var

STARTERS = ["How is the business performing in the last 4 weeks vs the prior period?", "Which regions declined the most last month?", "Why did revenue drop in the last 4 weeks?",
            "Show stockout impact by region", "Which promotions delivered the best lift?", "What business issues need attention right now?"]


def system_prompt(user, ctx):
    dv = C.dim_values()
    return f"""You are the CPG Analytics Copilot, a governed business-investigation assistant for a consumer packaged goods company.
STRICT RULES
1. You NEVER compute, estimate or recall numbers. Every number must come from a tool result. Call tools for every quantitative question.
2. Cite evidence right after each claim using the evidence label returned by tools, e.g. [E3]. Never invent labels.
3. If the request is genuinely ambiguous in a way that changes the analysis, call request_clarification (one question, 2-4 options). Otherwise pick sensible defaults (metric=revenue, period=last_4_weeks) and say so.
4. For "why / root cause / investigate / explain the drop" questions call start_investigation instead of improvising explanations.
5. Mention data limitations that tool results report (stale feeds, missing rows, scaled periods, unavailable evidence). Never conclude beyond the evidence.
6. Be concise: lead with the answer, then 2-5 short bullets. Plain language for business users.
7. If a tool returns an error, correct the arguments once if possible; policy errors must be relayed plainly.
CONTEXT
Latest data week starts {C.as_of()} (data through {C.as_of().isoformat()} + 6 days). Calendar words like "last month" are relative to the latest data date.
Metrics: {', '.join(S.METRICS)}. Regions: {', '.join(dv['region'])}. Channels: {', '.join(dv['channel'])}. Categories: {', '.join(dv['category'])}. Segments: {', '.join(dv['segment'])}.
Products: {', '.join(dv['product_name'])}.
User role: {user['role']}. Data-access scope: {json.dumps(user['scope']) if user['scope'] else 'unrestricted'}.
Current analytical context from earlier turns (reuse for follow-ups such as "and for South?"): {json.dumps(ctx)}"""


# ------------------------------------------------------------------ helpers
def _compact(res, label=None):
    if "error" in res:
        return json.dumps({"error": res["error"], "kind": res["kind"]})
    f = json.dumps(res["facts"], default=str)
    d = {"evidence_label": label, "headline": res["headline"], "rows": res["rows"][:12], "key_facts": f[:1400] if len(f) > 1400 else res["facts"], "limitations": res["limitations"][:3],
         "warnings": res.get("warnings", [])[:3], "data_quality": [i["detail"] for i in res["meta"]["data_quality"][:3]]}
    return json.dumps(d, default=str)[:4200]


def _numbers(o, acc):
    if isinstance(o, bool):
        return
    if isinstance(o, (int, float)):
        acc.add(float(o)); return
    if isinstance(o, dict):
        for v in o.values(): _numbers(v, acc)
    elif isinstance(o, list):
        for v in o: _numbers(v, acc)
    elif isinstance(o, str):
        for n in _parse_nums(o): acc.add(n[0])


NUM = re.compile(r"(?<![\w.])([-+]?)\$?(\d[\d,]*\.?\d*)\s?([KMB]|%)?(?![\w])")


def _parse_nums(text):
    out = []
    for m in NUM.finditer(text):
        try:
            v = float(m.group(2).replace(",", ""))
        except ValueError:
            continue
        mult = {"K": 1e3, "M": 1e6, "B": 1e9}.get(m.group(3) or "", 1)
        out.append((v * mult * (-1 if m.group(1) == "-" else 1), m.group(0).strip(), m.group(3) or ""))
    return out


def grounding(answer, results):
    acc = set()
    for r in results:
        _numbers(r.get("rows"), acc); _numbers(r.get("facts"), acc); _numbers(r.get("headline"), acc)
        _numbers(r.get("limitations"), acc); _numbers(r.get("warnings"), acc)
        _numbers([d.get("detail") for d in (r.get("meta") or {}).get("data_quality", [])], acc)
    cand = acc | {abs(a) for a in acc} | {a / 100 for a in acc} | {a * 100 for a in acc}
    text = re.sub(r"\[E\d+\]", "", answer); bad, n = [], 0
    for v, raw, suf in _parse_nums(text):
        if (1900 <= abs(v) <= 2100 and not suf and "." not in raw) or (abs(v) <= 12 and not suf and "$" not in raw and "." not in raw):
            continue
        n += 1
        if not any(abs(abs(v) - c) <= max(0.06, 0.02 * abs(c)) for c in cand):
            bad.append(raw)
    return {"checked": n, "unverified": sorted(set(bad))[:8]}


def suggestions(blocks, inv=None):
    s = []
    for b in blocks:
        t, f = b["tool"], b.get("facts", {})
        rows = b.get("rows_raw") or []
        if t in ("compare_periods", "performance_scorecard", "top_bottom", "variance_analysis") and rows:
            r0 = rows[0]; name = next((v for k, v in r0.items() if k in S.SALES_DIMS and isinstance(v, str)), None)
            if name:
                s += [f"Why did {name} change? Start an investigation", f"Break down {name} by product"]
        if t == "stockout_analysis":
            s += ["Which products need replenishment? Run inventory optimisation", "Estimate the revenue impact of these stockouts by region"]
        if t == "promotion_analysis":
            s += ["Did these promotions cannibalise related products?", "Show the business timeline with promotions"]
        if t == "driver_decomposition":
            s += ["Split this gap into price, volume and mix", "Start an investigation into this gap"]
        if t == "detect_business_issues":
            s += ["Investigate the top issue", "Show the business timeline for the last 26 weeks"]
        if t == "demand_forecast":
            s += ["Compare the forecast with safety stock requirements"]
        if t == "business_health_overview":
            s += ["What business issues need attention right now?", "Which regions declined the most?"]
    if inv:
        s += ["Show similar past issues and what worked", "What evidence is missing for this conclusion?", "Forecast demand for the affected scope"]
    s += ["Are there any data-quality issues I should know about?"]
    seen, out = set(), []
    for x_ in s:
        if x_ not in seen:
            seen.add(x_); out.append(x_)
    return out[:4]


# ------------------------------------------------------------------ offline planner
def offline_plan(message, ctx):
    p = nlu.parse(message); t = message.lower(); f = p["filters"]; per = p["period"]
    if not f and ctx.get("last_filters") and re.search(r"\b(and|what about|how about|same for|for)\b", t):
        f = ctx["last_filters"]
    per = per or (ctx.get("last_period") if re.search(r"\b(and|what about|how about|same)\b", t) else None)
    base = {k: v for k, v in {"period": per, "filters": f}.items() if v}
    cmp_ = {"compare_to": p["compare_to"]}
    has = lambda *ws: any(w in t for w in ws)
    follow = re.match(r"^\s*(and|what about|how about|same for|now)\b", t)
    if follow and ctx.get("last_tool") in ("compare_periods", "query_metric", "top_bottom", "trend_analysis", "performance_scorecard", "driver_decomposition", "stockout_analysis", "promotion_analysis", "variance_analysis", "drilldown", "price_volume_mix", "demand_forecast") and (f or per):
        a = dict(ctx.get("last_args") or {})
        if f: a["filters"] = f
        if per: a["period"] = per
        return ctx["last_tool"], a
    if has("quality", "fresh", "stale", "reliab", "missing data"): return "data_quality_check", base
    if has("why", "investigat", "root cause", "explain the", "reason for"):
        return "start_investigation", {"observation": message, **({"metric": p["metric"]} if p["metric"] in ("revenue", "units") else {}), **base, **cmp_}
    if has("issue", "radar", "need attention", "what should i look"): return "detect_business_issues", {}
    if has("health", "overview", "how are we", "how is the business"): return "business_health_overview", {}
    if has("anomal", "unusual", "abnormal"): return "anomaly_detection", {"metric": p["metric"], "group_by": p["group_by"] or ["region"], **({"filters": f} if f else {})}
    if has("forecast", "predict", "projection"): return "demand_forecast", {"metric": "revenue" if p["metric"] == "revenue" and "revenue" in t else "units", **({"filters": f} if f else {})}
    if has("elastic"): return "price_elasticity", {**({"product_name": f["product_name"][0]} if f.get("product_name") else {})}
    if has("price optim", "optimal price", "optimise price", "optimize price"):
        return ("price_optimization", {"product_name": f["product_name"][0]}) if f.get("product_name") else ("request_clarification", {"question": "Which product should I model price changes for?", "options": C.dim_values()["product_name"][:4]})
    if has("safety stock", "reorder", "replenish", "inventory optim"): return "inventory_optimization", {**({"filters": f} if f else {})}
    if has("cohort", "retention", "churn"): return "customer_cohorts", {**({"segment": f["segment"][0]} if f.get("segment") else {})}
    if has("competitor"): return "competitor_signals", {**base, **({"category": f["category"][0]} if f.get("category") else {})}
    if has("assortment", "pareto", "tail products"): return "assortment_analysis", base
    if has("cannibal"): return "promotion_analysis", {"analysis": "cannibalization", **base}
    if has("lift"): return "promotion_analysis", {"analysis": "lift", **base}
    if has("promo"): return "promotion_analysis", {"analysis": "impact", **base}
    if has("stockout", "out of stock", "availability"): return "stockout_analysis", {**base, **({"group_by": p["group_by"][:1]} if p["group_by"] else {})}
    if has("price volume", "price/volume", "pvm", "price, volume"): return "price_volume_mix", {"period": per or "last_12_weeks", **cmp_, **({"filters": f} if f else {})}
    if has("driver", "decompos", "what changed", "contribut", "drove", "driving", "what's behind"): return "driver_decomposition", {"period": per or "last_4_weeks", **cmp_, "metric": "units" if p["metric"] == "units" else "revenue", **({"filters": f} if f else {})}
    if has("variance", "benchmark"): return "variance_analysis", {"metric": p["metric"], **base}
    if has("quality", "fresh", "stale", "reliab"): return "data_quality_check", base
    if has("timeline"): return "business_timeline", {"metric": p["metric"], **({"filters": f} if f else {})}
    if has("similar", "past issue", "happened before", "previous"): return "recall_similar_issues", {"description": message}
    if has("drill", "break down", "breakdown"): return "drilldown", {"metric": p["metric"], "hierarchy": "geography" if "region" in t else "channel" if "channel" in t else "customer" if "segment" in t else "product", **base, **cmp_}
    if has("trend", "over time", "trajectory"): return "trend_analysis", {"metric": p["metric"], "grain": "month" if has("month", "quarter", "year") else "week", "period": per or "last_26_weeks", **({"filters": f} if f else {}), **({"group_by": p["group_by"][:1]} if p["group_by"] else {})}
    if has("top ", "bottom", "best", "worst", "highest", "lowest", "which "):
        return "top_bottom", {"metric": p["metric"], "group_by": p["group_by"] or ["product_name"], "n": p["n"], "order": p["order"], **base}
    if has("compare", "growth", "change", " vs ", "versus", "declin", "grew", "performance", "performing", "drop", "increase"):
        if p["group_by"] and has("performance", "performing", "scorecard"):
            return "performance_scorecard", {"dimension": p["group_by"][0], **base, **cmp_}
        multi = next((d for d, v in f.items() if len(v) > 1), None)
        gb = p["group_by"][:1] or ([multi] if multi else [])
        return "compare_periods", {"metric": p["metric"], "period": per or "last_4_weeks", **cmp_, **({"group_by": gb} if gb else {}), **({"filters": f} if f else {})}
    if has("revenue", "sales", "units", "margin", "price", "volume") or f or per:
        return "query_metric", {"metric": p["metric"], **({"group_by": p["group_by"][:1]} if p["group_by"] else {}), **base}
    return "request_clarification", {"question": "What would you like to look at?", "options": ["Revenue performance vs prior period", "Stockouts and availability", "Promotion effectiveness", "Business issues needing attention"]}


# ------------------------------------------------------------------ chat
class Turn:
    def __init__(self, user, conv_id, rid):
        self.user, self.conv_id, self.rid = user, conv_id, rid
        self.blocks, self.results, self.inv, self.clar, self.tools_log = [], [], None, None, []
        self.n = (q1("SELECT COUNT(*) c FROM evidence WHERE owner_type='conversation' AND owner_id=?", (conv_id,)) or {"c": 0})["c"]
        self.msg_id = uid("m_")

    def call(self, name, args):
        """Execute one governed tool call. Returns string content for the LLM."""
        import time
        t0 = time.time()
        if name == "request_clarification":
            self.clar = {"question": args.get("question", "Could you clarify?"), "options": (args.get("options") or [])[:4]}
            return json.dumps({"status": "clarification_requested"})
        if name == "start_investigation":
            try:
                inv = investigation.start(self.user, args.get("observation", "Investigate the movement"), {k: args.get(k) for k in ("metric", "period", "compare_to", "filters")}, self.conv_id, request_id=self.rid)
            except Exception as e:
                msg = str(e) or "Investigation could not be started."
                log("agent", logging.WARNING, "investigation failed", error=msg[:200]); return json.dumps({"error": msg[:300], "kind": "validation"})
            self.inv = inv
            self.tools_log.append({"name": name, "args": args, "ms": round((time.time() - t0) * 1000), "status": "ok"})
            s = inv["summary"]
            return json.dumps({"investigation_id": inv["id"], "title": inv["title"], "conclusion": s["conclusion"], "confidence": inv["confidence"]["level"], "narrative": s["narrative"],
                               "supported": [{"hypothesis": h["statement"], "explained_pct": h["explained_pct"], "evidence": h["evidence"]} for h in inv["hypotheses"] if h["status"] == "supported"],
                               "evidence_labels_are_investigation_scoped": True})
        if name == "recall_similar_issues":
            fake = {"id": "-", "title": args.get("description", ""), "observation": args.get("description", ""), "spec": {"filters": nlu.entities(args.get("description", "")), "metric": "revenue"}, "gap": {"delta": -1, "pct": None}, "hypotheses": []}
            sim = memory.find_similar(fake)
            res = {"headline": f"{len(sim)} similar past issue(s) found in institutional memory." + (f" Closest: {sim[0]['title']} (similarity {sim[0]['similarity']}; root cause: {sim[0]['root_cause']})." if sim else ""),
                   "rows": [{"title": s["title"], "similarity": s["similarity"], "root_cause": s["root_cause"], "outcome": (s["outcome"] or {}).get("result")} for s in sim], "chart": None,
                   "facts": {"similar": sim}, "limitations": ["Similarity combines text, entities, supported hypotheses and seasonality."], "columns": None,
                   "meta": {"tool": name, "args": args, "runtime_ms": 0, "sql": [], "tables": ["issue_memory"], "periods": [], "filters": {}, "policy": {"row_level_security": False}, "warnings": [], "freshness": {"sources": []}, "data_quality": [], "lineage": {"sources": [{"table": "issue_memory", "system": "Copilot", "refreshed": now()}], "transformations": ["TF-IDF + structural similarity"]}}}
        else:
            res = tools.execute(name, args, self.user, self.rid)
        ok = "error" not in res
        self.tools_log.append({"name": name, "args": args, "ms": round((time.time() - t0) * 1000), "status": "ok" if ok else res.get("kind", "error")})
        if not ok:
            return _compact(res)
        self.n += 1; label = f"E{self.n}"
        x("INSERT INTO evidence VALUES(?,?,?,?,?,?,?,?,?)", (uid("ev_"), "conversation", self.conv_id, label, self.msg_id, name, jd(args), jd(res), now()))
        self.results.append(res)
        self.blocks.append({"label": label, "tool": name, "args": args, "headline": res["headline"], "chart": res["chart"], "rows": res["rows"][:10], "rows_raw": res["rows"][:3], "facts": {k: v for k, v in res["facts"].items() if isinstance(v, (int, float, str)) and k != "tree"},
                            "limitations": res["limitations"][:3], "warnings": res.get("warnings", [])[:3], "freshness": res["meta"]["freshness"], "data_quality": res["meta"]["data_quality"][:3], "policy": res["meta"]["policy"], "runtime_ms": res["meta"]["runtime_ms"]})
        return _compact(res, label)


def _llm_loop(turn, user, message, history, ctx):
    msgs = [{"role": "system", "content": system_prompt(user, ctx)}, *history, {"role": "user", "content": message}]
    spec = tools.openai_tools(user["role"], message + " " + " ".join(h["content"] for h in history[-2:]))
    from .config import settings
    for _ in range(settings.max_tool_rounds):
        m = llm.chat(msgs, spec, "chat")
        if not m.tool_calls:
            return m.content or ""
        msgs.append({"role": "assistant", "content": m.content or "", "tool_calls": [{"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments or "{}"}} for tc in m.tool_calls]})
        for tc in m.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            msgs.append({"role": "tool", "tool_call_id": tc.id, "content": turn.call(tc.function.name, args)})
            if turn.clar:
                return turn.clar["question"]
    return llm.chat(msgs + [{"role": "user", "content": "Give your final answer now using the evidence gathered. Cite evidence labels."}], None, "chat_final").content or ""


def _offline(turn, message, ctx):
    name, args = offline_plan(message, ctx)
    out = turn.call(name, args)
    if turn.clar:
        return turn.clar["question"]
    if turn.inv:
        sm = turn.inv["summary"]
        return f"**{turn.inv['title']}**\n\n{sm['conclusion']}\n\n" + "\n".join("- " + c["text"] for c in sm["claims"] if c["kind"] == "finding")[:1800]
    if not turn.blocks:
        err = json.loads(out).get("error", "I could not run that analysis.")
        return f"I couldn't complete that: {err}"
    b = turn.blocks[0]; lines = [f"{b['headline']} [{b['label']}]"]
    for l in (b["limitations"] + b["warnings"])[:2]:
        lines.append(f"- Note: {l}")
    for d in b["data_quality"][:1]:
        lines.append(f"- Data quality: {d['detail']}")
    return "\n".join(lines)


def chat(user, message, conversation_id=None, request_id="-"):
    if conversation_id:
        conv = q1("SELECT * FROM conversations WHERE id=? AND user_id=?", (conversation_id, user["id"]))
        if not conv:
            raise LookupError("Conversation not found.")
    else:
        conv = {"id": uid("c_"), "user_id": user["id"], "title": message.strip()[:52] or "New conversation", "archived": 0, "context_json": jd({}), "created_at": now(), "updated_at": now()}
        x("INSERT INTO conversations VALUES(?,?,?,?,?,?,?)", (conv["id"], user["id"], conv["title"], 0, conv["context_json"], conv["created_at"], conv["updated_at"]))
    ctx = jl(conv["context_json"], {})
    hist = [{"role": r["role"], "content": r["content"][:1500]} for r in q("SELECT role, content FROM messages WHERE conversation_id=? ORDER BY created_at DESC LIMIT 8", (conv["id"],))][::-1]
    um = {"id": uid("m_"), "conversation_id": conv["id"], "role": "user", "content": message, "payload": None, "created_at": now()}
    x("INSERT INTO messages VALUES(?,?,?,?,?,?)", (um["id"], conv["id"], "user", message, None, um["created_at"]))
    turn = Turn(user, conv["id"], request_id); mode = "groq"
    try:
        if llm.available:
            try:
                answer = _llm_loop(turn, user, message, hist, ctx)
            except LLMUnavailable as e:
                log("agent", logging.WARNING, "llm unavailable, using offline planner", error=str(e)[:150]); mode = "offline (LLM unavailable)"
                turn.blocks, turn.results, turn.inv, turn.clar = [], [], None, None
                answer = _offline(turn, message, ctx)
        else:
            mode = "offline (no GROQ_API_KEY)"; answer = _offline(turn, message, ctx)
    except Exception as e:
        log("agent", logging.ERROR, "chat failure", error=repr(e)); answer = "Something went wrong while analysing that. The failure was logged with the request ID; please try rephrasing."
    if turn.inv:  # investigation evidence labels are scoped to the investigation workspace, not this conversation
        answer = re.sub(r"\s?\[E\d+\]", "", answer) + "\n\n_Full evidence, challenge analysis and replay are in the investigation below._"
    if turn.blocks and not re.search(r"\[E\d+\]", answer):
        answer += "\n\nEvidence: " + " ".join(f"[{b['label']}]" for b in turn.blocks)
    g = grounding(answer, turn.results + ([{"facts": {"i": turn.inv["summary"]["narrative"]}, "rows": [], "headline": turn.inv["summary"]["narrative"] + " " + turn.inv["summary"]["conclusion"] + " " + " ".join(c["text"] for c in turn.inv["summary"]["claims"])}] if turn.inv else []))
    last = turn.blocks[-1]["args"] if turn.blocks else {}
    ctx.update({k: v for k, v in {"last_tool": turn.blocks[-1]["tool"] if turn.blocks else ctx.get("last_tool"), "last_metric": last.get("metric") or ctx.get("last_metric"), "last_period": last.get("period") or ctx.get("last_period"),
                                  "last_filters": last.get("filters") or ctx.get("last_filters"), "last_investigation_id": turn.inv["id"] if turn.inv else ctx.get("last_investigation_id"), "last_args": last or ctx.get("last_args")}.items() if v})
    payload = {"mode": mode, "evidence": [{k: v for k, v in b.items() if k not in ("rows_raw",)} for b in turn.blocks], "suggestions": suggestions(turn.blocks, turn.inv) if not turn.clar else [], "clarification": turn.clar, "grounding": g, "tools": turn.tools_log,
               "investigation": {"id": turn.inv["id"], "title": turn.inv["title"], "confidence": turn.inv["confidence"], "conclusion": turn.inv["summary"]["conclusion"], "gap": turn.inv["gap"],
                                 "hypotheses": [{"key": h["key"], "statement": h["statement"], "status": h["status"], "explained_pct": h["explained_pct"]} for h in turn.inv["hypotheses"] if h["category"] == "Cause"][:5]} if turn.inv else None, "request_id": request_id}
    am = {"id": turn.msg_id, "conversation_id": conv["id"], "role": "assistant", "content": answer, "payload": payload, "created_at": now()}
    x("INSERT INTO messages VALUES(?,?,?,?,?,?)", (am["id"], conv["id"], "assistant", answer, jd(payload), am["created_at"]))
    x("UPDATE conversations SET context_json=?, updated_at=? WHERE id=?", (jd(ctx), now(), conv["id"]))
    audit(user, "chat", {"conversation": conv["id"], "tools": [t["name"] for t in turn.tools_log], "evidence": [b["label"] for b in turn.blocks], "mode": mode, "output_chars": len(answer), "unverified_numbers": len(g["unverified"])})
    return {"conversation": {k: conv[k] for k in ("id", "title", "archived", "created_at")} | {"updated_at": now()}, "user_message": um, "assistant_message": am}


def starter_suggestions():
    rows = q("SELECT data_json, score FROM radar_issues WHERE status='new' ORDER BY score DESC LIMIT 2")
    out = [f"Investigate: {jl(r['data_json'])['title']}" for r in rows]
    return (out + STARTERS)[:6]
