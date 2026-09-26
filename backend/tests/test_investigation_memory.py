from fastapi.testclient import TestClient

from app.agent.investigation_session import (
    investigation_session_manager,
)
from app.agent.session import conversation_manager
from app.main import app


client = TestClient(app)


def setup_function():
    conversation_manager.sessions.clear()
    investigation_session_manager.sessions.clear()


def test_investigation_is_stored_in_conversation_history(
    monkeypatch,
):
    def fake_prepare_investigation(
        question,
        investigation_id,
    ):
        return {
            "question": question,
            "history": [],
            "plan": [
                "revenue_trend",
                "regional_performance",
            ],
            "hypotheses": [
                {
                    "id": "H1",
                    "statement": (
                        "Revenue may be changing "
                        "because of regional performance."
                    ),
                    "evidence_targets": [
                        "regional_performance"
                    ],
                }
            ],
            "evidence": {
                "revenue_trend": {
                    "direction": "down",
                    "change_pct": -8.2,
                }
            },
        }

    def fake_stream_synthesis(
        question,
        evidence,
        hypotheses,
        history,
    ):
        yield "Revenue declined "
        yield "primarily in the South region."

    monkeypatch.setattr(
        "app.main.prepare_investigation",
        fake_prepare_investigation,
    )

    monkeypatch.setattr(
        "app.main.stream_synthesis",
        fake_stream_synthesis,
    )

    response = client.post(
        "/api/investigate/stream",
        json={
            "conversation_id": "investigation-test-1",
            "message": "Why is revenue changing?",
        },
    )

    assert response.status_code == 200

    conversation = (
        conversation_manager.get_conversation(
            "investigation-test-1"
        )
    )

    assert conversation["history"] == [
        {
            "role": "user",
            "content": "Why is revenue changing?",
        },
        {
            "role": "assistant",
            "content": (
                "Revenue declined "
                "primarily in the South region."
            ),
        },
    ]


def test_investigation_memory_stores_analytical_context(
    monkeypatch,
):
    def fake_prepare_investigation(
        question,
        investigation_id,
    ):
        return {
            "question": question,
            "history": [],
            "plan": [
                "revenue_trend",
                "product_performance",
            ],
            "hypotheses": [],
            "evidence": {
                "revenue_trend": {
                    "direction": "down",
                    "change_pct": -12.5,
                }
            },
        }

    def fake_stream_synthesis(
        question,
        evidence,
        hypotheses,
        history,
    ):
        yield "Revenue declined."

    monkeypatch.setattr(
        "app.main.prepare_investigation",
        fake_prepare_investigation,
    )

    monkeypatch.setattr(
        "app.main.stream_synthesis",
        fake_stream_synthesis,
    )

    response = client.post(
        "/api/investigate/stream",
        json={
            "conversation_id": "investigation-test-2",
            "message": "Why is revenue down?",
        },
    )

    assert response.status_code == 200

    investigation = (
        investigation_session_manager
        .get_latest_investigation(
            "investigation-test-2"
        )
    )

    assert investigation["plan"] == [
        "revenue_trend",
        "product_performance",
    ]

    assert investigation["evidence"] == {
        "revenue_trend": {
            "direction": "down",
            "change_pct": -12.5,
        }
    }

    assert investigation["answer"] == (
        "Revenue declined."
    )


def test_chat_and_investigation_share_conversation_id(
    monkeypatch,
):
    def fake_agent_run(
        user_message,
        history=None,
    ):
        return {
            "answer": "Revenue is stable.",
            "tools_used": [],
            "tool_results": [],
        }

    def fake_prepare_investigation(
        question,
        investigation_id,
    ):
        return {
            "question": question,
            "history": [],
            "plan": ["revenue_trend"],
            "hypotheses": [],
            "evidence": {
                "revenue_trend": {
                    "direction": "stable"
                }
            },
        }

    def fake_stream_synthesis(
        question,
        evidence,
        hypotheses,
        history,
    ):
        yield "The investigation found stable revenue."

    monkeypatch.setattr(
        "app.main.agent.run",
        fake_agent_run,
    )

    monkeypatch.setattr(
        "app.main.prepare_investigation",
        fake_prepare_investigation,
    )

    monkeypatch.setattr(
        "app.main.stream_synthesis",
        fake_stream_synthesis,
    )

    conversation_id = "shared-conversation"

    chat_response = client.post(
        "/api/chat",
        json={
            "conversation_id": conversation_id,
            "message": "Give me a quick revenue summary.",
        },
    )

    assert chat_response.status_code == 200

    investigation_response = client.post(
        "/api/investigate/stream",
        json={
            "conversation_id": conversation_id,
            "message": "Why is revenue changing?",
        },
    )

    assert investigation_response.status_code == 200

    conversation = (
        conversation_manager.get_conversation(
            conversation_id
        )
    )

    assert len(conversation["history"]) == 4

    assert conversation["history"][0] == {
        "role": "user",
        "content": "Give me a quick revenue summary.",
    }

    assert conversation["history"][1] == {
        "role": "assistant",
        "content": "Revenue is stable.",
    }

    assert conversation["history"][2] == {
        "role": "user",
        "content": "Why is revenue changing?",
    }

    assert conversation["history"][3] == {
        "role": "assistant",
        "content": (
            "The investigation found stable revenue."
        ),
    }

    investigation = (
        investigation_session_manager
        .get_latest_investigation(
            conversation_id
        )
    )

    assert investigation["plan"] == [
        "revenue_trend"
    ]


def test_investigation_sessions_remain_isolated():
    investigation_session_manager.add_message(
        "investigation-a",
        {
            "role": "user",
            "content": "Question A",
        },
    )

    investigation_session_manager.update_investigation(
        "investigation-a",
        plan=["revenue_trend"],
        evidence={"revenue": "down"},
        answer="Revenue declined.",
    )

    investigation_session_manager.add_message(
        "investigation-b",
        {
            "role": "user",
            "content": "Question B",
        },
    )

    investigation_b = (
        investigation_session_manager
        .get_latest_investigation(
            "investigation-b"
        )
    )

    assert investigation_b["plan"] == []
    assert investigation_b["evidence"] == {}
    assert investigation_b["answer"] == ""

    assert (
        investigation_session_manager
        .get_history("investigation-b")
        == [
            {
                "role": "user",
                "content": "Question B",
            }
        ]
    )