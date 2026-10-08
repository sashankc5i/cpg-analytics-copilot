"""OBS-004 / OBS-005: LLM and tool telemetry."""
import numpy as np

from .db import now, q, uid, x


def record_llm(request_id, model, purpose, latency_ms, status, pt=0, ct=0, error=None):
    x("INSERT INTO llm_calls VALUES(?,?,?,?,?,?,?,?,?,?)", (uid("l_"), now(), request_id, model, purpose, latency_ms, status, pt, ct, (error or "")[:300]))


def record_tool(request_id, user_id, tool, latency_ms, status, error=None):
    x("INSERT INTO tool_calls VALUES(?,?,?,?,?,?,?,?)", (uid("t_"), now(), request_id, user_id, tool, latency_ms, status, (error or "")[:300]))


def _stats(rows, key):
    out = {}
    for r in rows:
        out.setdefault(r[key], []).append(r)
    res = []
    for k, rs in out.items():
        lat = [r["latency_ms"] for r in rs]
        res.append({"name": k, "calls": len(rs), "failures": sum(r["status"] != "ok" for r in rs), "p50_ms": round(float(np.percentile(lat, 50))), "p95_ms": round(float(np.percentile(lat, 95))),
                    **({"prompt_tokens": sum(r["prompt_tokens"] or 0 for r in rs), "completion_tokens": sum(r["completion_tokens"] or 0 for r in rs)} if "prompt_tokens" in rs[0] else {})})
    return sorted(res, key=lambda r: -r["calls"])


def summary():
    llm = q("SELECT * FROM llm_calls ORDER BY ts DESC LIMIT 2000"); tools = q("SELECT * FROM tool_calls ORDER BY ts DESC LIMIT 5000")
    return {"llm": {"total_calls": len(llm), "failures": sum(r["status"] != "ok" for r in llm), "prompt_tokens": sum(r["prompt_tokens"] or 0 for r in llm), "completion_tokens": sum(r["completion_tokens"] or 0 for r in llm),
                    "by_model": _stats(llm, "model"), "by_purpose": _stats(llm, "purpose"), "recent_errors": [r for r in llm if r["status"] != "ok"][:5]},
            "tools": {"total_calls": len(tools), "failures": sum(r["status"] != "ok" for r in tools), "by_tool": _stats(tools, "tool"), "recent_errors": [r for r in tools if r["status"] != "ok"][:5]}}
