from typing import Any


CONFIDENCE_LEVELS = (
    (80, "high"),
    (60, "moderate"),
    (0, "low"),
)


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return min(1.0, max(0.0, numerator / denominator))


def _confidence_level(score: float) -> str:
    for threshold, level in CONFIDENCE_LEVELS:
        if score >= threshold:
            return level
    return "low"


def calculate_confidence(
    *,
    plan: list[str],
    evidence: dict[str, Any],
    hypotheses: list[dict[str, Any]],
    claims: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Calculate an evidence-coverage confidence score.

    This is deliberately deterministic. The score is NOT a probability
    that the conclusion is true. It measures how completely the
    investigation is supported by the evidence collected by the
    approved analytics layer.
    """

    planned_count = len(set(plan))
    evidence_count = len(evidence)
    hypothesis_count = len(hypotheses)
    claim_count = len(claims)

    traceable_claims = sum(
        1
        for claim in claims
        if claim.get("traceability_status") == "traceable"
        and claim.get("evidence_refs")
    )

    hypotheses_with_evidence = sum(
        1
        for hypothesis in hypotheses
        if hypothesis.get("evidence")
    )

    investigation_coverage = _ratio(
        evidence_count,
        planned_count,
    )

    hypothesis_coverage = _ratio(
        hypotheses_with_evidence,
        hypothesis_count,
    )

    claim_traceability = _ratio(
        traceable_claims,
        claim_count,
    )

    evidence_breadth = min(
        1.0,
        evidence_count / 3.0,
    )

    if not evidence_count:
        score = 0.0
    else:
        score = (
            investigation_coverage * 35
            + hypothesis_coverage * 25
            + claim_traceability * 30
            + evidence_breadth * 10
        )

    score = round(min(100.0, max(0.0, score)), 1)

    limitations: list[str] = []

    if planned_count > evidence_count:
        limitations.append(
            "Not all planned investigations returned evidence."
        )

    if hypothesis_count and hypotheses_with_evidence < hypothesis_count:
        limitations.append(
            "Some hypotheses do not have collected evidence."
        )

    if claim_count and traceable_claims < claim_count:
        limitations.append(
            "Some generated claims are not fully traceable."
        )

    if not claims:
        limitations.append(
            "No validated claims were generated."
        )

    if not evidence:
        limitations.append(
            "No deterministic evidence was collected."
        )

    return {
        "score": score,
        "level": _confidence_level(score),
        "basis": "evidence_coverage",
        "signals": {
            "investigation_coverage": round(
                investigation_coverage * 100,
                1,
            ),
            "hypothesis_evidence_coverage": round(
                hypothesis_coverage * 100,
                1,
            ),
            "claim_traceability": round(
                claim_traceability * 100,
                1,
            ),
            "evidence_breadth": round(
                evidence_breadth * 100,
                1,
            ),
        },
        "counts": {
            "planned_investigations": planned_count,
            "evidence_sources": evidence_count,
            "hypotheses": hypothesis_count,
            "claims": claim_count,
            "traceable_claims": traceable_claims,
        },
        "limitations": limitations,
    }
