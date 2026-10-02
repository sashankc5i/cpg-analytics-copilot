from app.agent.investigation_session import investigation_session_manager


def test_generate_claims_validates_against_evidence(
    monkeypatch,
):
    from app.agent.investigation import (
        generate_claims,
    )

    class FakeResponse:
        class Choice:
            class Message:
                content = """
                {
                    "claims": [
                        {
                            "id": "C1",
                            "statement": "South generated the highest revenue.",
                            "evidence_refs": [
                                {
                                    "investigation": "regional_performance",
                                    "field": "revenue",
                                    "entity": "South"
                                }
                            ]
                        },
                        {
                            "id": "C2",
                            "statement": "North generated the highest revenue.",
                            "evidence_refs": [
                                {
                                    "investigation": "regional_performance",
                                    "field": "revenue",
                                    "entity": "North"
                                }
                            ]
                        }
                    ]
                }
                """

            message = Message()

        choices = [
            Choice()
        ]

    def fake_create(**kwargs):
        return FakeResponse()

    monkeypatch.setattr(
        "app.agent.investigation.client.chat.completions.create",
        fake_create,
    )

    result = generate_claims(
        {
            "question": "Which region generated the most revenue?",
            "history": [],
            "hypotheses": [],
            "plan": [
                "regional_performance"
            ],
            "evidence": {
                "regional_performance": [
                    {
                        "region": "South",
                        "revenue": 120000,
                    }
                ]
            },
            "claims": [],
            "answer": "",
        }
    )

    assert len(result["claims"]) == 1

    assert result["claims"][0]["id"] == "C1"

    assert (
        result["claims"][0]["traceability_status"]
        == "traceable"
    )


def test_generate_claims_returns_empty_when_no_evidence(
    monkeypatch,
):
    from app.agent.investigation import (
        generate_claims,
    )

    def fail_if_called(**kwargs):
        raise AssertionError(
            "LLM should not be called without evidence."
        )

    monkeypatch.setattr(
        "app.agent.investigation.client.chat.completions.create",
        fail_if_called,
    )

    result = generate_claims(
        {
            "question": "Why is revenue changing?",
            "history": [],
            "hypotheses": [],
            "plan": [],
            "evidence": {},
            "claims": [],
            "answer": "",
        }
    )

    assert result == {
        "claims": []
    }


def test_synthesis_prompt_contains_traceable_claims():
    from app.agent.investigation import (
        get_synthesis_prompt,
    )

    prompt = get_synthesis_prompt(
        question="Why is revenue changing?",
        evidence={
            "regional_performance": [
                {
                    "region": "South",
                    "revenue": 120000,
                }
            ]
        },
        hypotheses=[],
        history=[],
        claims=[
            {
                "id": "C1",
                "statement": (
                    "South generated the highest revenue."
                ),
                "status": "unverified",
                "evidence_refs": [
                    {
                        "investigation": (
                            "regional_performance"
                        ),
                        "field": "revenue",
                        "entity": "South",
                    }
                ],
                "traceability_status": "traceable",
            }
        ],
    )

    assert "TRACEABLE CANDIDATE CLAIMS" in prompt
    assert "South generated the highest revenue." in prompt
    assert "regional_performance" in prompt
def test_update_investigation_stores_claims():
    claims = [
        {
            "id": "C1",
            "statement": (
                "South generated the highest revenue."
            ),
            "status": "unverified",
            "evidence_refs": [
                {
                    "investigation": (
                        "regional_performance"
                    ),
                    "field": "revenue",
                    "entity": "South",
                }
            ],
            "traceability_status": "traceable",
        }
    ]

    investigation_session_manager.update_investigation(
        "investigation-claims",
        plan=["regional_performance"],
        evidence={
            "regional_performance": [
                {
                    "region": "South",
                    "revenue": 120000,
                }
            ]
        },
        claims=claims,
        answer="South generated the highest revenue.",
    )

    stored = (
        investigation_session_manager
        .get_latest_investigation(
            "investigation-claims"
        )
    )

    assert stored["claims"] == claims


def test_update_investigation_copies_claims():
    claims = [
        {
            "id": "C1",
            "statement": "Revenue declined.",
            "status": "unverified",
            "evidence_refs": [
                {
                    "investigation": "revenue_trend",
                    "field": "revenue",
                    "entity": "2026-08",
                }
            ],
            "traceability_status": "traceable",
        }
    ]

    investigation_session_manager.update_investigation(
        "investigation-claims-copy",
        plan=["revenue_trend"],
        evidence={
            "revenue_trend": [
                {
                    "month": "2026-08",
                    "revenue": 100000,
                }
            ]
        },
        claims=claims,
        answer="Revenue declined.",
    )

    claims[0]["statement"] = (
        "Modified externally."
    )

    claims[0]["evidence_refs"][0][
        "entity"
    ] = "Modified externally."

    stored = (
        investigation_session_manager
        .get_latest_investigation(
            "investigation-claims-copy"
        )
    )

    assert stored["claims"][0]["statement"] == (
        "Revenue declined."
    )

    assert stored["claims"][0]["evidence_refs"][0][
        "entity"
    ] == "2026-08"


def test_get_latest_investigation_returns_claim_copy():
    investigation_session_manager.update_investigation(
        "investigation-claims-defensive",
        plan=["regional_performance"],
        evidence={
            "regional_performance": [
                {
                    "region": "South",
                    "revenue": 120000,
                }
            ]
        },
        claims=[
            {
                "id": "C1",
                "statement": (
                    "South generated the highest revenue."
                ),
                "status": "unverified",
                "evidence_refs": [
                    {
                        "investigation": (
                            "regional_performance"
                        ),
                        "field": "revenue",
                        "entity": "South",
                    }
                ],
                "traceability_status": "traceable",
            }
        ],
        answer="South generated the highest revenue.",
    )

    investigation = (
        investigation_session_manager
        .get_latest_investigation(
            "investigation-claims-defensive"
        )
    )

    investigation["claims"][0]["statement"] = (
        "Modified externally."
    )

    investigation["claims"][0][
        "evidence_refs"
    ][0]["entity"] = "West"

    stored = (
        investigation_session_manager
        .get_latest_investigation(
            "investigation-claims-defensive"
        )
    )

    assert stored["claims"][0]["statement"] == (
        "South generated the highest revenue."
    )

    assert stored["claims"][0][
        "evidence_refs"
    ][0]["entity"] == "South"


def test_clear_resets_claims():
    investigation_session_manager.update_investigation(
        "investigation-clear-claims",
        plan=["regional_performance"],
        evidence={
            "regional_performance": [
                {
                    "region": "South",
                    "revenue": 120000,
                }
            ]
        },
        claims=[
            {
                "id": "C1",
                "statement": (
                    "South generated the highest revenue."
                ),
                "status": "unverified",
                "evidence_refs": [
                    {
                        "investigation": (
                            "regional_performance"
                        ),
                        "field": "revenue",
                        "entity": "South",
                    }
                ],
                "traceability_status": "traceable",
            }
        ],
        answer="South generated the highest revenue.",
    )

    investigation_session_manager.clear(
        "investigation-clear-claims"
    )

    investigation = (
        investigation_session_manager
        .get_latest_investigation(
            "investigation-clear-claims"
        )
    )

    assert investigation["claims"] == []