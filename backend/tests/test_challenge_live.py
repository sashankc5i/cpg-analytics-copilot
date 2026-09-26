from app.agent.challenge import challenge_planner


def test_live_challenge_planner():

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
        "challenge_plan": [],
        "challenge_evidence": {},
        "challenge_answer": "",
    }

    result = challenge_planner(state)

    plan = result["challenge_plan"]

    assert isinstance(plan, list)
    assert len(plan) > 0

    for investigation in plan:
        assert investigation in {
            "revenue_trend",
            "regional_performance",
            "product_performance",
            "category_performance",
            "customer_segments",
            "promotion_impact",
            "inventory_stockouts",
        }

    print("\nChallenge plan:")

    for investigation in plan:
        print(f"- {investigation}")