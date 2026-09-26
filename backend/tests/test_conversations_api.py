from fastapi.testclient import TestClient

from app.main import app
from app.agent.session import conversation_manager


client = TestClient(app)


def setup_function():
    conversation_manager.sessions.clear()


def test_create_conversation():
    response = client.post(
        "/api/conversations",
        json={
            "title": "Sales Investigation",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["title"] == "Sales Investigation"
    assert data["archived"] is False
    assert data["history"] == []
    assert data["conversation_id"]


def test_create_conversation_with_custom_id():
    response = client.post(
        "/api/conversations",
        json={
            "conversation_id": "custom-session",
            "title": "Custom Session",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["conversation_id"] == "custom-session"
    assert data["title"] == "Custom Session"


def test_list_conversations():
    client.post(
        "/api/conversations",
        json={"title": "Conversation A"},
    )

    client.post(
        "/api/conversations",
        json={"title": "Conversation B"},
    )

    response = client.get("/api/conversations")

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 2
    assert {item["title"] for item in data} == {
        "Conversation A",
        "Conversation B",
    }


def test_get_conversation():
    create_response = client.post(
        "/api/conversations",
        json={
            "conversation_id": "conversation-1",
            "title": "Revenue Analysis",
        },
    )

    assert create_response.status_code == 200

    response = client.get(
        "/api/conversations/conversation-1"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["conversation_id"] == "conversation-1"
    assert data["title"] == "Revenue Analysis"
    assert data["history"] == []


def test_rename_conversation():
    client.post(
        "/api/conversations",
        json={
            "conversation_id": "rename-test",
            "title": "Old Title",
        },
    )

    response = client.patch(
        "/api/conversations/rename-test",
        json={
            "title": "New Title",
        },
    )

    assert response.status_code == 200
    assert response.json()["title"] == "New Title"


def test_archive_conversation():
    client.post(
        "/api/conversations",
        json={
            "conversation_id": "archive-test",
            "title": "Archive Me",
        },
    )

    response = client.post(
        "/api/conversations/archive-test/archive"
    )

    assert response.status_code == 200
    assert response.json()["archived"] is True

    list_response = client.get(
        "/api/conversations"
    )

    assert list_response.status_code == 200
    assert list_response.json() == []


def test_unarchive_conversation():
    client.post(
        "/api/conversations",
        json={
            "conversation_id": "unarchive-test",
            "title": "Restore Me",
        },
    )

    client.post(
        "/api/conversations/unarchive-test/archive"
    )

    response = client.post(
        "/api/conversations/unarchive-test/unarchive"
    )

    assert response.status_code == 200
    assert response.json()["archived"] is False

    list_response = client.get(
        "/api/conversations"
    )

    assert len(list_response.json()) == 1


def test_delete_conversation():
    client.post(
        "/api/conversations",
        json={
            "conversation_id": "delete-test",
            "title": "Delete Me",
        },
    )

    response = client.delete(
        "/api/conversations/delete-test"
    )

    assert response.status_code == 200

    assert response.json() == {
        "conversation_id": "delete-test",
        "deleted": True,
    }

    get_response = client.get(
        "/api/conversations/delete-test"
    )

    assert get_response.status_code == 200


def test_delete_missing_conversation():
    response = client.delete(
        "/api/conversations/does-not-exist"
    )

    assert response.status_code == 404