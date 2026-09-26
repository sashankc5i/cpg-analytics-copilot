from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_challenge_requires_completed_investigation():

    conversation_id = (
        "challenge-test-no-investigation"
    )

    response = client.post(
        "/api/investigate/challenge/stream",
        json={
            "message": "Challenge this conclusion",
            "conversation_id": conversation_id,
        },
    )

    assert response.status_code == 400

    body = response.json()

    assert (
        "No completed investigation"
        in body["detail"]
    )


def test_challenge_stream_uses_investigation_session():

    conversation_id = (
        "challenge-test-with-investigation"
    )

    fake_challenge = {
        "question": "Why did revenue decline?",
        "original_answer": (
            "Regional performance contributed "
            "to the decline."
        ),
        "claims": [
            {
                "id": "C1",
                "claim": (
                    "Regional performance contributed "
                    "to the decline."
                ),
                "type": "causal",
                "status": "partially_supported",
            }
        ],
        "challenge_plan": [
            "regional_performance",
        ],
        "challenge_evidence": {
            "regional_performance": {
                "tool": "get_sales_by_region",
                "result": [],
            }
        },
        "challenge_answer": "",
    }

    fake_chunks = [
        "The conclusion ",
        "is partially supported.",
    ]

    with patch(
        "app.main.prepare_challenge",
        return_value=fake_challenge,
    ), patch(
        "app.main.stream_challenge_synthesis",
        return_value=iter(fake_chunks),
    ):

        response = client.post(
            "/api/investigate/challenge/stream",
            json={
                "message": "Challenge this conclusion",
                "conversation_id": conversation_id,
            },
        )

    assert response.status_code == 200

    lines = [
        line
        for line in response.text.splitlines()
        if line.strip()
    ]

    assert len(lines) > 0

    events = [
        __import__("json").loads(line)
        for line in lines
    ]

    event_types = [
        event["type"]
        for event in events
    ]

    assert (
        "challenge_started"
        in event_types
    )

    assert "claims" in event_types

    assert (
        "challenge_plan"
        in event_types
    )

    assert (
        "challenge_evidence"
        in event_types
    )

    assert "answer_start" in event_types

    assert event_types.count("token") == 2

    assert "answer_end" in event_types

    assert events[-1]["type"] == "answer_end"