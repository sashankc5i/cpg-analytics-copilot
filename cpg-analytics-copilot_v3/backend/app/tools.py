"""Governed tool registry (TRU-008): allow-listed, schema-validated, scope-enforced, telemetered."""
import json
import time
from dataclasses import dataclass
from typing import Callable, Optional

import jsonschema

from . import semantic as S
from .analytics import commercial as CM
from .analytics import core as C
from .analytics import ops, performance as P, pulse
from .analytics.errors import PolicyError, ToolError
from .db import q
from .logging_setup import log
from .security import ROLES
from .telemetry import record_tool
import logging

M = {"type": "string", "enum": list(S.METRICS), "description": "Governed metric key"}
PER = {"type": "string", "description": "last_4_weeks, last_12_weeks, last_month, last_quarter, ytd, 2026-Q2, 2026-08 or YYYY-MM-DD..YYYY-MM-DD. Calendar words are relative to the latest data date."}
CMP = {"type": "string", "enum": ["prior_period", "prior_year", "none"], "description": "Comparison basis"}
GB = {"type": "array", "items": {"type": "string", "enum": S.SALES_DIMS}, "maxItems": 2}
FILT = {"type": "object", "description": "Exact-name filters, e.g. {\"region\":[\"South\"]}. Keys: region, channel, category, brand, product_name, segment.", "additionalProperties": {"type": "array", "items": {"type": "string"}}}
INT = lambda d, lo=1, hi=50: {"type": "integer", "minimum": lo, "maximum": hi, "description": d}


def sch(props, req=()):
    return {"type": "object", "properties": props, "required": list(req)}


@dataclass
class Tool:
    name: str
    desc: str
    schema: dict
    fn: Optional[Callable]
    tier: str
    keywords: tuple = ()


T = [
    Tool("query_metric", "Get a governed KPI for a period, optionally grouped/filtered.", sch({"metric": M, "group_by": GB, "filters": FILT, "period": PER, "limit": INT("max rows")}, ["metric"]), P.query_metric, "core"),
    Tool("compare_periods", "Compare a metric between two periods (MoM/QoQ/YoY/prior period), optionally by dimension. Use for growth, change, performance questions.",
         sch({"metric": M, "period": PER, "compare_to": CMP, "group_by": GB, "filters": FILT, "limit": INT("max rows")}, ["metric", "period"]), P.compare_periods, "core"),
    Tool("top_bottom", "Rank top or bottom members of a dimension by a metric (max 25).", sch({"metric": M, "group_by": GB, "n": INT("how many", 1, 25), "order": {"type": "string", "enum": ["top", "bottom"]}, "period": PER, "filters": FILT}, ["metric", "group_by"]), P.top_bottom, "core"),
    Tool("trend_analysis", "Trend of a metric over time (week/month/quarter) with material movements.", sch({"metric": M, "grain": {"type": "string", "enum": ["week", "month", "quarter"]}, "period": PER, "filters": FILT, "group_by": GB}, ["metric"]), P.trend_analysis, "core", ("trend", "over time", "trajectory")),
    Tool("variance_analysis", "Explain variance vs prior period/prior year/trailing average with contributors and a bridge.", sch({"metric": M, "period": PER, "benchmark": {"type": "string", "enum": ["prior_period", "prior_year", "trailing_avg"]}, "dimension": {"type": "string", "enum": S.SALES_DIMS}, "filters": FILT}, ["metric"]), P.variance_analysis, "core", ("variance", "benchmark", "vs plan", "gap")),
    Tool("drilldown", "Hierarchical drill-down (product: category>brand>product; geography; channel; customer).", sch({"metric": M, "hierarchy": {"type": "string", "enum": list(S.HIERARCHIES)}, "period": PER, "compare_to": CMP, "filters": FILT, "level": {"type": "string"}}, ["metric"]), P.drilldown, "core", ("drill", "break down", "breakdown", "within")),
    Tool("performance_scorecard", "Multi-KPI scorecard (revenue, growth, share, price, margin, promo share) for a dimension: product, category, region, channel, segment, brand.", sch({"dimension": {"type": "string", "enum": S.SALES_DIMS}, "period": PER, "compare_to": CMP, "filters": FILT}, ["dimension"]), P.performance_scorecard, "core", ("scorecard", "performance", "channel", "segment", "region", "category", "product")),
    Tool("driver_decomposition", "Decompose a revenue/units gap into contributors across region, category, channel, segment, product with a driver tree and price/volume/mix.", sch({"period": PER, "compare_to": CMP, "metric": {"type": "string", "enum": ["revenue", "units"]}, "filters": FILT}, ["period"]), P.driver_decomposition, "core", ("driver", "decompos", "contribut", "what changed")),
    Tool("price_volume_mix", "Split revenue change into volume, mix, list price and promo/discount effects.", sch({"period": PER, "compare_to": CMP, "filters": FILT}, ["period"]), P.price_volume_mix, "core", ("price", "volume", "mix", "pvm")),
    Tool("anomaly_detection", "Detect unusual metric movement versus a seasonally adjusted historical baseline, optionally per dimension member.", sch({"metric": M, "group_by": GB, "filters": FILT, "eval_weeks": INT("weeks to evaluate", 2, 26)}), P.anomaly_detection, "core", ("anomal", "unusual", "abnormal", "spike", "outlier")),
    Tool("business_health_overview", "Executive overview of KPIs, movers and anomalies.", sch({"period": PER}), pulse.business_health_overview, "core", ("health", "overview", "how are we", "pulse", "summary")),
    Tool("detect_business_issues", "Business Issue Radar: material issues ranked by materiality with cross-domain correlation.", sch({"limit": INT("max issues", 1, 15)}), pulse.detect_business_issues, "core", ("issue", "radar", "attention", "problem", "risk")),
    Tool("business_timeline", "Timeline of a KPI with promotions, stockouts, price changes and competitor events.", sch({"metric": M, "period": PER, "filters": FILT}), pulse.business_timeline, "core", ("timeline", "events", "when")),
    Tool("data_quality_check", "Data quality findings and freshness of source feeds.", sch({"period": PER, "filters": FILT}), ops.data_quality_check, "core", ("quality", "fresh", "stale", "reliab", "missing data", "refresh")),
    Tool("promotion_analysis", "Promotion impact, lift vs baseline, or cannibalisation of substitutes.", sch({"analysis": {"type": "string", "enum": ["impact", "lift", "cannibalization"]}, "period": PER, "compare_to": CMP, "filters": FILT}, ["analysis"]), CM.promotion_analysis, "adv", ("promo", "lift", "cannibal", "discount")),
    Tool("stockout_analysis", "Stockout rates and estimated lost sales, by product/region.", sch({"period": PER, "compare_to": CMP, "group_by": {"type": "array", "items": {"type": "string", "enum": ["region", "product_name", "category", "brand"]}, "maxItems": 2}, "filters": FILT}), ops.stockout_analysis, "adv", ("stockout", "out of stock", "availability", "inventory")),
    Tool("assortment_analysis", "Product assortment ABC / Pareto analysis with growth and margin flags.", sch({"period": PER, "compare_to": CMP, "filters": FILT}), CM.assortment_analysis, "adv", ("assortment", "range", "sku", "tail", "pareto")),
    Tool("customer_cohorts", "Customer cohort retention by segment.", sch({"segment": {"type": "string"}}), CM.customer_cohorts, "adv", ("cohort", "retention", "churn")),
    Tool("competitor_signals", "Governed external competitor price/promo signals and association with our sales.", sch({"category": {"type": "string"}, "period": PER, "compare_to": CMP}), CM.competitor_signals, "adv", ("competitor", "market", "rival")),
    Tool("price_elasticity", "Estimate price elasticity of demand with confidence intervals.", sch({"product_name": {"type": "string"}, "filters": FILT}), CM.price_elasticity, "adv", ("elastic", "price sensitiv")),
    Tool("demand_forecast", "Forecast units or revenue with uncertainty intervals.", sch({"metric": {"type": "string", "enum": ["units", "revenue"]}, "horizon_weeks": INT("weeks ahead", 1, 26), "filters": FILT, "group_by": GB}), ops.demand_forecast, "dec", ("forecast", "predict", "next quarter", "next month", "projection")),
    Tool("inventory_optimization", "Safety stock, reorder point and replenish/reduce recommendations by product-region.", sch({"service_level": {"type": "number", "minimum": 0.5, "maximum": 0.998}, "lead_time_weeks": {"type": "number", "minimum": 0.5, "maximum": 12}, "max_weeks_cover": {"type": "number", "minimum": 1, "maximum": 26}, "filters": FILT}), ops.inventory_optimization, "dec", ("safety stock", "reorder", "replenish", "optimi")),
    Tool("price_optimization", "What-if price optimisation for one product using estimated elasticity (withheld if unreliable).", sch({"product_name": {"type": "string"}, "filters": FILT, "min_volume_change_pct": {"type": "number", "minimum": -30, "maximum": 0}, "assumed_elasticity": {"type": "number", "maximum": 0}}, ["product_name"]), CM.price_optimization, "dec", ("price optim", "optimal price", "pricing")),
    Tool("recall_similar_issues", "Search institutional memory for similar past investigations and their hypotheses/outcomes.", sch({"description": {"type": "string"}}, ["description"]), None, "core", ("similar", "before", "history", "past", "previous")),
    Tool("start_investigation", "Start a structured investigation (plan, hypotheses, evidence, challenge). Use for why/root-cause/investigate questions.",
         sch({"observation": {"type": "string", "description": "The business observation to explain"}, "metric": {"type": "string", "enum": ["revenue", "units"]}, "period": PER, "compare_to": CMP, "filters": FILT}, ["observation"]), None, "core", ("why", "investigat", "root cause", "explain", "reason", "cause")),
    Tool("request_clarification", "Ask ONE targeted clarifying question only when the request is genuinely ambiguous.", sch({"question": {"type": "string"}, "options": {"type": "array", "items": {"type": "string"}, "maxItems": 4}}, ["question"]), None, "core"),
]
TOOLS = {t.name: t for t in T}
LINEAGE_STEPS = ["Governed, parameterised SQL aggregation (no LLM-generated SQL)", "Row-level security filters applied from user scope", "Deterministic pandas calculations", "LLM used only to interpret intent and narrate results"]


def allowed(role):
    return [t for t in T if t.name in ROLES[role]["tools"]]


def openai_tools(role, message=None, subset=True):
    ts = allowed(role)
    if subset and message:
        m = message.lower(); core = {"query_metric", "compare_periods", "top_bottom", "start_investigation", "request_clarification", "performance_scorecard", "driver_decomposition"}
        ts = [t for t in ts if t.name in core or any(k in m for k in t.keywords)]
    return [{"type": "function", "function": {"name": t.name, "description": t.desc, "parameters": t.schema}} for t in ts]


def _coerce(args, schema):
    out = {}
    props = schema["properties"]
    for k, v in (args or {}).items():
        if k not in props:
            continue
        t = props[k].get("type")
        if t == "array" and isinstance(v, str):
            v = [v]
        elif t == "integer" and isinstance(v, (str, float)):
            try: v = int(float(v))
            except ValueError: pass
        elif t == "number" and isinstance(v, str):
            try: v = float(v)
            except ValueError: pass
        elif t == "object" and isinstance(v, str):
            try: v = json.loads(v)
            except ValueError: pass
        if k == "filters" and isinstance(v, dict):
            v = {kk: ([vv] if isinstance(vv, str) else vv) for kk, vv in v.items()}
        out[k] = v
    return out


def _meta(ctx, name, args, ms):
    seen, sqls = set(), []
    for s in ctx.sqls:
        if s["sql"] not in seen:
            seen.add(s["sql"]); sqls.append(s)
    fr = ops.freshness_info(ctx)
    return {"tool": name, "args": args, "runtime_ms": round(ms), "sql": sqls[:6], "tables": sorted(ctx.tables), "periods": [p.to_dict() for p in ctx.periods[:4]], "filters": ctx.filters,
            "policy": {"row_level_security": ctx.scoped, "scope": ctx.scope if ctx.scoped else {}}, "warnings": ctx.warnings,
            "freshness": {"data_through": (C.as_of() + __import__("datetime").timedelta(days=6)).isoformat(), "latest_week": C.as_of().isoformat(), "sources": fr},
            "data_quality": ops.dq_relevant(ctx), "lineage": {"sources": [{"table": f["table"], "system": f["system"], "refreshed": f["last_refreshed"]} for f in fr], "transformations": LINEAGE_STEPS,
                                                           "metric": args.get("metric")}}


def execute(name, args, user, request_id="-"):
    t0 = time.time(); status, err = "ok", None
    try:
        td = TOOLS.get(name)
        if not td or td.fn is None:
            raise ToolError(f"Unknown tool '{name}'.")
        if name not in ROLES[user["role"]]["tools"]:
            raise PolicyError(f"Your role ({user['role']}) is not permitted to run {name}.")
        a = _coerce(args, td.schema)
        try:
            jsonschema.validate(a, td.schema)
        except jsonschema.ValidationError as e:
            raise ToolError(f"Invalid arguments: {e.message}")
        ctx = C.Ctx(scope=user["scope"], user=user, request_id=request_id)
        res = td.fn(ctx, **a)
        res["meta"] = _meta(ctx, name, a, (time.time() - t0) * 1000)
        res["warnings"] = ctx.warnings
        return res
    except ToolError as e:
        status, err = "validation_error", str(e); return {"error": str(e), "kind": "validation"}
    except PolicyError as e:
        status, err = "policy_denied", str(e); return {"error": str(e), "kind": "policy"}
    except Exception as e:  # never leak raw internals
        status, err = "error", repr(e)
        log("tools", logging.ERROR, "tool failure", tool=name, error=repr(e))
        return {"error": "The analytics tool failed unexpectedly. The failure was logged with the request ID.", "kind": "internal"}
    finally:
        record_tool(request_id, user["id"], name, (time.time() - t0) * 1000, status, err)
