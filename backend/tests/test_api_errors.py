import json

from fastapi.testclient import TestClient

from app.main import app
from app.agent.investigation_session import (
    investigation_session_manager,
)
from app.agent.session import conversation_manager


client = TestClient(app)


def setup_function():
    conversation_manager.sessions.clear()
    investigation_session_manager.sessions.clear()


def test_chat_runtime_error_returns_safe_response(monkeypatch):
    def failing_agent_run(
        user_message,
        history=None,
        analytical_context=None,
    ):
        raise RuntimeError(
            "Sensitive provider failure: GROQ_SECRET_INTERNAL_DETAIL"
        )

    monkeypatch.setattr(
        "app.main.agent.run",
        failing_agent_run,
    )

    response = client.post(
        "/api/chat",
        json={
            "conversation_id": "error-test",
            "message": "What happened to revenue?",
        },
    )

    assert response.status_code == 500

    data = response.json()

    assert data["detail"]["message"] == (
        "The analytics service could not process the request."
    )
    assert data["detail"]["request_id"]
    assert "GROQ_SECRET_INTERNAL_DETAIL" not in response.text


def test_chat_unexpected_error_returns_safe_response(monkeypatch):
    def failing_agent_run(
        user_message,
        history=None,
        analytical_context=None,
    ):
        raise Exception(
            "Sensitive unexpected failure: INTERNAL_STACK_DETAIL"
        )

    monkeypatch.setattr(
        "app.main.agent.run",
        failing_agent_run,
    )

    response = client.post(
        "/api/chat",
        json={
            "conversation_id": "unexpected-error-test",
            "message": "Show me revenue.",
        },
    )

    assert response.status_code == 500

    data = response.json()

    assert data["detail"]["message"] == (
        "An unexpected error occurred."
    )
    assert data["detail"]["request_id"]
    assert "INTERNAL_STACK_DETAIL" not in response.text


def test_readiness_failure_returns_safe_response(monkeypatch):
    monkeypatch.setattr(
        "app.main.settings.groq_api_key",
        "",
    )

    response = client.get("/readiness")

    assert response.status_code == 503

    data = response.json()

    assert data["detail"]["status"] == "not_ready"
    assert data["detail"]["message"] == (
        "Service dependencies are not ready."
    )
    assert data["detail"]["request_id"]
    assert "Groq API key is not configured." not in response.text


def _read_ndjson(response):
    return [
        json.loads(line)
        for line in response.text.splitlines()
        if line.strip()
    ]


def test_investigation_stream_failure_returns_safe_error(
    monkeypatch,
):
    def fake_prepare_investigation(
        question,
        investigation_id,
    ):
        return {
            "question": question,
            "history": [],
            "plan": [],
            "hypotheses": [],
            "evidence": {},
        }

    def failing_stream_synthesis(*args, **kwargs):
        raise RuntimeError(
            "Sensitive investigation failure: "
            "INTERNAL_INVESTIGATION_DETAIL"
        )

    monkeypatch.setattr(
        "app.main.prepare_investigation",
        fake_prepare_investigation,
    )

    monkeypatch.setattr(
        "app.main.stream_synthesis",
        failing_stream_synthesis,
    )

    response = client.post(
        "/api/investigate/stream",
        json={
            "conversation_id": (
                "investigation-stream-error-test"
            ),
            "message": "Why did revenue change?",
        },
    )

    assert response.status_code == 200

    events = [
        json.loads(line)
        for line in response.text.strip().splitlines()
    ]

    error_events = [
        event
        for event in events
        if event.get("type") == "error"
    ]

    assert len(error_events) == 1

    error_data = error_events[0]["data"]

    assert (
        error_data["message"]
        == "The investigation could not be completed."
    )

    assert (
        error_data["request_id"]
        == response.headers["X-Request-ID"]
    )

    assert (
        "INTERNAL_INVESTIGATION_DETAIL"
        not in response.text
    )


def test_challenge_stream_failure_returns_safe_error(monkeypatch):
    def fake_prepare_challenge(investigation_id):
        return {
            "question": "Why did revenue decline?",
            "original_answer": (
                "Revenue declined in the latest period."
            ),
            "claims": [],
            "challenge_plan": [],
            "challenge_evidence": [],
        }

    def failing_stream_challenge_synthesis(
        question,
        original_answer,
        claims,
        evidence,
    ):
        raise RuntimeError(
            "Sensitive challenge failure: INTERNAL_CHALLENGE_DETAIL"
        )

    monkeypatch.setattr(
        "app.main.prepare_challenge",
        fake_prepare_challenge,
    )

    monkeypatch.setattr(
        "app.main.stream_challenge_synthesis",
        failing_stream_challenge_synthesis,
    )

    response = client.post(
        "/api/investigate/challenge/stream",
        json={
            "conversation_id": "challenge-error-test",
            "message": "Challenge the conclusion.",
        },
    )

    assert response.status_code == 200

    lines = [
        line
        for line in response.text.splitlines()
        if line.strip()
    ]

    error_events = [
        json.loads(line)
        for line in lines
        if json.loads(line).get("type") == "error"
    ]

    assert error_events

    error_event = error_events[-1]

    assert error_event["data"]["message"] == (
        "The challenge could not be completed."
    )

    assert error_event["data"]["request_id"]

    assert (
        "INTERNAL_CHALLENGE_DETAIL"
        not in response.text
    )


def test_investigation_start_failure_returns_safe_response(
    monkeypatch,
):
    def failing_prepare(*args, **kwargs):
        raise RuntimeError(
            "Sensitive preparation failure: INTERNAL_PREP_DETAIL"
        )

    monkeypatch.setattr(
        "app.main.prepare_investigation",
        failing_prepare,
    )

    response = client.post(
        "/api/investigate/stream",
        json={
            "conversation_id": "investigation-start-error-test",
            "message": "Investigate revenue.",
        },
    )

    assert response.status_code == 500

    data = response.json()

    assert data["detail"]["message"] == (
        "Unable to start investigation."
    )
    assert data["detail"]["request_id"]
    assert "INTERNAL_PREP_DETAIL" not in response.text