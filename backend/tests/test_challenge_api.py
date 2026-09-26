from unittest.mock import patch

import app.agent.challenge as challenge
from app.agent.investigation_session import (
    investigation_session_manager,
)


def _seed_session(investigation_id: str):
    investigation_session_manager.sessions[investigation_id] = {
        "history": [
            {
                "role": "user",
                "content": "Why did revenue change?",
            }
        ],
        "latest_plan": [
            "revenue_trend",
            "regional_performance",
        ],
        "latest_evidence": {
            "revenue_trend": {
                "tool": "get_monthly_sales_trend",
                "result": [
                    {
                        "month": "2026-01",
                        "revenue": 1000,
                    },
                    {
                        "month": "2026-02",
                        "revenue": 900,
                    },
                ],
            },
            "regional_performance": {
                "tool": "get_sales_by_region",
                "result": [
                    {
                        "region": "West",
                        "revenue": 500,
                    },
                    {
                        "region": "South",
                        "revenue": 400,
                    },
                ],
            },
        },
        "latest_answer": (
            "Revenue declined because West region "
            "performance weakened."
        ),
    }


def test_prepare_challenge_reuses_existing_investigation():
    investigation_id = "test-direct-review-api"

    _seed_session(investigation_id)

    with patch.object(
        challenge.client.chat.completions,
        "create",
    ) as create:
        result = challenge.prepare_challenge(
            investigation_id
        )

    create.assert_not_called()

    assert result["question"] == (
        "Why did revenue change?"
    )

    assert (
        "West region"
        in result["original_answer"]
    )

    assert result["claims"] == []

    assert result["challenge_plan"] == [
        "revenue_trend",
        "regional_performance",
    ]

    assert (
        "revenue_trend"
        in result["challenge_evidence"]
    )


def test_challenge_prompt_contains_conclusion_and_evidence():
    prompt = challenge.get_challenge_prompt(
        question="Why did revenue change?",
        original_answer=(
            "Revenue declined because West region "
            "performance weakened."
        ),
        evidence={
            "regional_performance": {
                "result": [
                    {
                        "region": "West",
                        "revenue": 500,
                    },
                ]
            }
        },
    )

    assert "West region" in prompt
    assert "regional_performance" in prompt

    assert (
        "Do not treat correlation as causation."
        in prompt
    )

    assert "Never invent metrics" in prompt


def test_build_challenge_evidence_digest():
    evidence = {
        "regional_performance": {
            "tool": "get_sales_by_region",
            "result": [
                {
                    "region": "West",
                    "revenue": 500,
                },
            ],
        }
    }

    digest = (
        challenge.build_challenge_evidence_digest(
            evidence
        )
    )

    assert digest == {
        "regional_performance": {
            "row_count": 1,
            "rows": [
                {
                    "region": "West",
                    "revenue": 500,
                },
            ],
        }
    }


def test_prepare_challenge_requires_completed_investigation():
    investigation_id = "test-empty-review-api"

    investigation_session_manager.sessions[
        investigation_id
    ] = {
        "history": [],
        "latest_plan": [],
        "latest_evidence": {},
        "latest_answer": "",
    }

    with patch.object(
        challenge.client.chat.completions,
        "create",
    ) as create:

        try:
            challenge.prepare_challenge(
                investigation_id
            )

        except ValueError as error:
            assert (
                "No completed investigation"
                in str(error)
            )

        else:
            raise AssertionError(
                "Expected ValueError"
            )

    create.assert_not_called()