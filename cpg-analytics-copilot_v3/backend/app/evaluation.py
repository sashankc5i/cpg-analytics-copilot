"""Persist lightweight, reproducible checks for recent assistant messages."""
import re

from . import db


def evaluate_recent(limit=100):
    rows = db.q("SELECT m.id,m.conversation_id,m.content,m.payload_json,m.created_at FROM messages m WHERE m.role='assistant' ORDER BY m.created_at DESC LIMIT ?", (limit,))
    saved = 0
    for row in rows:
        payload = db.jl(row.get("payload_json"), {}) or {}
        evidence = payload.get("evidence", [])
        expected = {item.get("label") for item in evidence if item.get("label")}
        cited = set(re.findall(r"\[(E\d+)\]", row["content"] or ""))
        citation = len(cited & expected) / max(1, len(cited)) if cited else (1.0 if not expected else 0.0)
        # This score is a grounding proxy, not a human or model judgment of truth.
        grounded = 0.5 * citation + (0.5 if expected and cited else 0.25 if not expected else 0.0)
        latency = db.q1("SELECT AVG(latency_ms) AS n FROM llm_calls WHERE ts>=?", (row["created_at"],))
        db.x("INSERT INTO evaluation_results VALUES(?,?,?,?,?,?,?,?)", (db.uid("ev_"), row["conversation_id"], row["id"], round(grounded, 3), round(citation, 3), (latency or {}).get("n"), db.jd({"method": "citation/evidence grounding heuristic", "citation_count": len(cited), "evidence_count": len(expected)}), db.now()))
        saved += 1
    return {"evaluated": saved}


def report():
    return db.q1("SELECT COUNT(*) AS evaluations, AVG(accuracy) AS avg_accuracy, AVG(citation_correctness) AS avg_citation_correctness, AVG(latency_ms) AS avg_latency_ms, MAX(created_at) AS latest_at FROM evaluation_results") or {}
