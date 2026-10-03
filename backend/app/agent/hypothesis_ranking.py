from __future__ import annotations

from typing import Any


def rank_hypotheses(
    hypotheses: list[dict[str, Any]],
    evidence: dict[str, Any],
) -> list[dict[str, Any]]:
    """Rank hypotheses by deterministic evidence coverage.

    The score measures how much of the hypothesis' required analytical
    evidence was actually collected. It is not a probability that the
    hypothesis is true.
    """
    ranked = []
    for hypothesis in hypotheses or []:
        required = [
            item for item in hypothesis.get("required_investigations", [])
            if isinstance(item, str)
        ]
        available = [item for item in required if item in (evidence or {})]
        coverage = 0.0 if not required else len(available) / len(required)
        evidence_count = len(hypothesis.get("evidence", {}) or {})
        status = hypothesis.get("status", "unverified")
        status_bonus = {
            "supported": 0.15,
            "partially_supported": 0.05,
            "unverified": 0.0,
            "not_supported": -0.10,
        }.get(status, 0.0)
        score = max(0.0, min(1.0, coverage + status_bonus))
        item = dict(hypothesis)
        item["ranking"] = {
            "score": round(score * 100, 1),
            "evidence_coverage": round(coverage * 100, 1),
            "evidence_sources": evidence_count,
            "basis": "deterministic_evidence_coverage",
        }
        ranked.append(item)

    ranked.sort(
        key=lambda item: (
            item["ranking"]["score"],
            item["ranking"]["evidence_sources"],
        ),
        reverse=True,
    )

    for index, item in enumerate(ranked, start=1):
        item["rank"] = index

    return ranked
