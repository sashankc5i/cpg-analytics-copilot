from app.agent.challenge import evaluate_claims


def test_live_claim_evaluation():

    state = {
        "question": "Why did revenue decline?",
        "original_answer": (
            "Regional performance appears to have "
            "contributed to the decline. South and "
            "East showed weaker revenue performance, "
            "although the evidence does not establish "
            "that regional performance was the primary "
            "cause."
        ),
        "hypotheses": [],
        "evidence": {},
        "claims": [
            {
                "id": "C1",
                "claim": (
                    "Regional performance contributed "
                    "to the decline."
                ),
                "type": "causal",
                "investigations": [
                    "regional_performance",
                    "revenue_trend",
                ],
                "status": "unchallenged",
                "supporting_evidence": [],
                "contradicting_evidence": [],
                "missing_evidence": [],
            },
            {
                "id": "C2",
                "claim": (
                    "South and East showed weaker "
                    "regional performance."
                ),
                "type": "comparative",
                "investigations": [
                    "regional_performance",
                ],
                "status": "unchallenged",
                "supporting_evidence": [],
                "contradicting_evidence": [],
                "missing_evidence": [],
            },
        ],
        "challenge_plan": [
            "regional_performance",
            "revenue_trend",
        ],
        "challenge_evidence": {
            "regional_performance": {
                "tool": "get_sales_by_region",
                "result": [
                    {
                        "region": "South",
                        "revenue": 1000,
                    },
                    {
                        "region": "West",
                        "revenue": 1500,
                    },
                    {
                        "region": "North",
                        "revenue": 1300,
                    },
                    {
                        "region": "East",
                        "revenue": 900,
                    },
                ],
            },
            "revenue_trend": {
                "tool": "get_monthly_sales_trend",
                "result": [
                    {
                        "month": "2026-01",
                        "revenue": 15000,
                    },
                    {
                        "month": "2026-02",
                        "revenue": 14000,
                    },
                ],
            },
        },
        "challenge_answer": "",
    }

    result = evaluate_claims(state)

    claims = result["claims"]

    assert isinstance(claims, list)
    assert len(claims) == 2

    valid_statuses = {
        "supported",
        "partially_supported",
        "contradicted",
        "insufficient_evidence",
    }

    print("\nEvaluated claims:")

    for claim in claims:

        assert claim["status"] in valid_statuses

        assert isinstance(
            claim["supporting_evidence"],
            list,
        )

        assert isinstance(
            claim["contradicting_evidence"],
            list,
        )

        assert isinstance(
            claim["missing_evidence"],
            list,
        )

        print(
            f"\n{claim['id']}"
            f" | {claim['status']}"
        )

        print(
            "Supporting:",
            claim["supporting_evidence"],
        )

        print(
            "Contradicting:",
            claim["contradicting_evidence"],
        )

        print(
            "Missing:",
            claim["missing_evidence"],
        )