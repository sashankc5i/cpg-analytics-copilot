from unittest.mock import patch

from app.agent.challenge import (
    build_challenge_plan,
    challenge_planner,
    evaluate_claims,
    validate_claims,
)


def test_validate_claims_accepts_valid_claim():
    claims = [
        {
            "id": "C1",
            "claim": (
                "Regional performance contributed "
                "to the revenue decline."
            ),
            "type": "causal",
            "investigations": [
                "regional_performance",
                "revenue_trend",
            ],
        }
    ]

    result = validate_claims(claims)

    assert len(result) == 1
    assert result[0]["id"] == "C1"
    assert result[0]["type"] == "causal"
    assert (
        result[0]["status"]
        == "unchallenged"
    )


def test_validate_claims_rejects_invalid_investigation():
    claims = [
        {
            "id": "C1",
            "claim": "Something happened.",
            "type": "descriptive",
            "investigations": [
                "made_up_investigation",
            ],
        }
    ]

    result = validate_claims(claims)

    assert result == []


def test_validate_claims_rejects_invalid_claim_type():
    claims = [
        {
            "id": "C1",
            "claim": "Something happened.",
            "type": "prediction",
            "investigations": [
                "regional_performance",
            ],
        }
    ]

    result = validate_claims(claims)

    assert result == []


def test_challenge_plan_deduplicates_investigations():
    claims = [
        {
            "id": "C1",
            "claim": "Regional performance declined.",
            "type": "descriptive",
            "investigations": [
                "regional_performance",
                "revenue_trend",
            ],
        },
        {
            "id": "C2",
            "claim": "Product mix may explain the decline.",
            "type": "causal",
            "investigations": [
                "revenue_trend",
                "product_performance",
            ],
        },
    ]

    plan = build_challenge_plan(claims)

    assert plan == [
        "regional_performance",
        "revenue_trend",
        "product_performance",
    ]


def test_challenge_plan_empty_claims():
    assert build_challenge_plan([]) == []


def test_extract_claims_from_llm_response():
    fake_response = {
        "claims": [
            {
                "id": "C1",
                "claim": (
                    "Regional performance contributed "
                    "to the revenue decline."
                ),
                "type": "causal",
                "investigations": [
                    "regional_performance",
                    "revenue_trend",
                ],
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
            },
        ]
    }

    claims = validate_claims(
        fake_response["claims"]
    )

    assert len(claims) == 2

    assert claims[0]["id"] == "C1"
    assert claims[0]["type"] == "causal"
    assert (
        claims[0]["status"]
        == "unchallenged"
    )

    assert claims[1]["id"] == "C2"
    assert claims[1]["type"] == "comparative"


def test_challenge_planner_accepts_only_approved_investigations():
    state = {
        "question": "Why did revenue decline?",
        "original_answer": (
            "Regional performance contributed "
            "to the decline."
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
            }
        ],
        "challenge_plan": [],
        "challenge_evidence": {},
        "challenge_answer": "",
    }

    class FakeMessage:
        content = (
            '{"investigations": ['
            '"regional_performance", '
            '"revenue_trend", '
            '"made_up_investigation"'
            ']}'
        )

    class FakeChoice:
        message = FakeMessage()

    class FakeResponse:
        choices = [FakeChoice()]

    class FakeCompletions:
        def create(self, **kwargs):
            return FakeResponse()

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        chat = FakeChat()

    with patch(
        "app.agent.challenge.client",
        FakeClient(),
    ):
        result = challenge_planner(state)

    assert result["challenge_plan"] == [
        "regional_performance",
        "revenue_trend",
    ]


def test_evaluate_claims_updates_claim_status():
    state = {
        "question": "Why did revenue decline?",
        "original_answer": (
            "Regional performance contributed "
            "to the decline."
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
            }
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
                    }
                ],
            },
            "revenue_trend": {
                "tool": "get_monthly_sales_trend",
                "result": [
                    {
                        "month": "2026-01",
                        "revenue": 1200,
                    },
                    {
                        "month": "2026-02",
                        "revenue": 1000,
                    },
                ],
            },
        },
        "challenge_answer": "",
    }

    class FakeMessage:
        content = """
        {
            "claims": [
                {
                    "id": "C1",
                    "status": "partially_supported",
                    "supporting_evidence": [
                        "Regional revenue data shows measurable regional performance differences."
                    ],
                    "contradicting_evidence": [],
                    "missing_evidence": [
                        "The available evidence does not establish regional performance as the primary cause."
                    ]
                }
            ]
        }
        """

    class FakeChoice:
        message = FakeMessage()

    class FakeResponse:
        choices = [FakeChoice()]

    class FakeCompletions:
        def create(self, **kwargs):
            return FakeResponse()

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        chat = FakeChat()

    with patch(
        "app.agent.challenge.client",
        FakeClient(),
    ):
        result = evaluate_claims(state)

    claims = result["claims"]

    assert len(claims) == 1

    assert (
        claims[0]["status"]
        == "partially_supported"
    )

    assert len(
        claims[0]["supporting_evidence"]
    ) == 1

    assert len(
        claims[0]["missing_evidence"]
    ) == 1