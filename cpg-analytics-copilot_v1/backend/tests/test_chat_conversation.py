from fastapi.testclient import TestClient

from app.agent.session import conversation_manager
from app.main import app


client = TestClient(app)


def setup_function():
    conversation_manager.sessions.clear()


def test_chat_creates_and_updates_conversation_history(
    monkeypatch,
):
    def fake_agent_run(
        user_message,
        history=None,
    ):
        assert user_message == "What is our revenue trend?"
        assert history == []

        return {
            "answer": "Revenue is relatively stable.",
            "tools_used": ["get_monthly_sales_trend"],
            "tool_results": [],
        }

    monkeypatch.setattr(
        "app.main.agent.run",
        fake_agent_run,
    )

    response = client.post(
        "/api/chat",
        json={
            "conversation_id": "chat-test-1",
            "message": "What is our revenue trend?",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["conversation_id"] == "chat-test-1"
    assert data["answer"] == "Revenue is relatively stable."

    conversation = conversation_manager.get_conversation(
        "chat-test-1"
    )

    assert conversation["conversation_id"] == "chat-test-1"

    assert conversation["history"] == [
        {
            "role": "user",
            "content": "What is our revenue trend?",
        },
        {
            "role": "assistant",
            "content": "Revenue is relatively stable.",
        },
    ]


def test_chat_reuses_existing_conversation_history(
    monkeypatch,
):
    conversation_manager.create(
        "chat-test-2",
        title="Revenue Analysis",
    )

    conversation_manager.add_message(
        "chat-test-2",
        {
            "role": "user",
            "content": "What happened to revenue last month?",
        },
    )

    conversation_manager.add_message(
        "chat-test-2",
        {
            "role": "assistant",
            "content": "Revenue declined slightly last month.",
        },
    )

    captured_history = None

    def fake_agent_run(
        user_message,
        history=None,
    ):
        nonlocal captured_history

        captured_history = list(history)

        return {
            "answer": "The latest trend is stable.",
            "tools_used": [],
            "tool_results": [],
        }

    monkeypatch.setattr(
        "app.main.agent.run",
        fake_agent_run,
    )

    response = client.post(
        "/api/chat",
        json={
            "conversation_id": "chat-test-2",
            "message": "What is happening now?",
        },
    )

    assert response.status_code == 200

    assert captured_history == [
        {
            "role": "user",
            "content": "What happened to revenue last month?",
        },
        {
            "role": "assistant",
            "content": "Revenue declined slightly last month.",
        },
    ]

    conversation = conversation_manager.get_conversation(
        "chat-test-2"
    )

    assert conversation["history"] == [
        {
            "role": "user",
            "content": "What happened to revenue last month?",
        },
        {
            "role": "assistant",
            "content": "Revenue declined slightly last month.",
        },
        {
            "role": "user",
            "content": "What is happening now?",
        },
        {
            "role": "assistant",
            "content": "The latest trend is stable.",
        },
    ]


def test_chat_updates_conversation_timestamp(
    monkeypatch,
):
    conversation_manager.create(
        "chat-test-3",
        title="Timestamp Test",
    )

    before = conversation_manager.get_session(
        "chat-test-3"
    )["updated_at"]

    def fake_agent_run(
        user_message,
        history=None,
    ):
        return {
            "answer": "Test response.",
            "tools_used": [],
            "tool_results": [],
        }

    monkeypatch.setattr(
        "app.main.agent.run",
        fake_agent_run,
    )

    response = client.post(
        "/api/chat",
        json={
            "conversation_id": "chat-test-3",
            "message": "Hello",
        },
    )

    assert response.status_code == 200

    after = conversation_manager.get_session(
        "chat-test-3"
    )["updated_at"]

    assert after >= before


def test_different_conversations_have_independent_history(
    monkeypatch,
):
    def fake_agent_run(
        user_message,
        history=None,
    ):
        return {
            "answer": f"Response to: {user_message}",
            "tools_used": [],
            "tool_results": [],
        }

    monkeypatch.setattr(
        "app.main.agent.run",
        fake_agent_run,
    )

    first_response = client.post(
        "/api/chat",
        json={
            "conversation_id": "conversation-a",
            "message": "Question A",
        },
    )

    second_response = client.post(
        "/api/chat",
        json={
            "conversation_id": "conversation-b",
            "message": "Question B",
        },
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    first_conversation = (
        conversation_manager.get_conversation(
            "conversation-a"
        )
    )

    second_conversation = (
        conversation_manager.get_conversation(
            "conversation-b"
        )
    )

    assert first_conversation["history"] == [
        {
            "role": "user",
            "content": "Question A",
        },
        {
            "role": "assistant",
            "content": "Response to: Question A",
        },
    ]

    assert second_conversation["history"] == [
        {
            "role": "user",
            "content": "Question B",
        },
        {
            "role": "assistant",
            "content": "Response to: Question B",
        },
    ]