from app.agent.session import (
    ConversationManager,
)


ConversationSessionManager = ConversationManager


def test_create_conversation():
    manager = ConversationManager()

    conversation = manager.create(
        "conversation-1",
        title="Revenue Analysis",
    )

    assert conversation[
        "conversation_id"
    ] == "conversation-1"

    assert conversation[
        "title"
    ] == "Revenue Analysis"

    assert conversation[
        "archived"
    ] is False

    assert conversation[
        "history"
    ] == []


def test_get_session_creates_missing_conversation():
    manager = ConversationManager()

    conversation = manager.get_session(
        "conversation-1"
    )

    assert conversation[
        "conversation_id"
    ] == "conversation-1"

    assert conversation[
        "title"
    ] == "New Chat"


def test_add_message_updates_history():
    manager = ConversationManager()

    manager.add_message(
        "conversation-1",
        {
            "role": "user",
            "content": "Why did revenue decline?",
        },
    )

    history = manager.get_history(
        "conversation-1"
    )

    assert len(history) == 1
    assert history[0]["role"] == "user"
    assert (
        history[0]["content"]
        == "Why did revenue decline?"
    )


def test_get_history_returns_defensive_copy():
    manager = ConversationManager()

    manager.add_message(
        "conversation-1",
        {
            "role": "user",
            "content": "Show revenue",
        },
    )

    history = manager.get_history(
        "conversation-1"
    )

    history.clear()

    stored_history = manager.get_history(
        "conversation-1"
    )

    assert len(stored_history) == 1
    assert (
        stored_history[0]["content"]
        == "Show revenue"
    )


def test_get_history_protects_message_objects():
    manager = ConversationManager()

    manager.add_message(
        "conversation-1",
        {
            "role": "user",
            "content": "Show revenue",
        },
    )

    history = manager.get_history(
        "conversation-1"
    )

    history[0]["content"] = "Modified externally"

    stored_history = manager.get_history(
        "conversation-1"
    )

    assert (
        stored_history[0]["content"]
        == "Show revenue"
    )


def test_add_message_copies_input_message():
    manager = ConversationManager()

    message = {
        "role": "user",
        "content": "Show revenue",
    }

    manager.add_message(
        "conversation-1",
        message,
    )

    message["content"] = "Modified externally"

    history = manager.get_history(
        "conversation-1"
    )

    assert (
        history[0]["content"]
        == "Show revenue"
    )


def test_list_sessions_excludes_archived_by_default():
    manager = ConversationSessionManager()

    manager.create(
        "conversation-1",
        title="Active Chat",
    )

    manager.create(
        "conversation-2",
        title="Archived Chat",
    )

    manager.archive("conversation-2")

    sessions = manager.list_sessions()

    ids = {
        session["conversation_id"]
        for session in sessions
    }

    assert "conversation-1" in ids
    assert "conversation-2" not in ids


def test_list_sessions_can_include_archived():
    manager = ConversationSessionManager()

    manager.create(
        "conversation-1",
        title="Active Chat",
    )

    manager.create(
        "conversation-2",
        title="Archived Chat",
    )

    manager.archive("conversation-2")

    sessions = manager.list_sessions(
        include_archived=True
    )

    ids = {
        session["conversation_id"]
        for session in sessions
    }

    assert "conversation-1" in ids
    assert "conversation-2" in ids


def test_rename_conversation():
    manager = ConversationSessionManager()

    manager.create(
        "conversation-1",
        title="New Chat",
    )

    conversation = manager.rename(
        "conversation-1",
        "Revenue Investigation",
    )

    assert (
        conversation["title"]
        == "Revenue Investigation"
    )


def test_archive_and_unarchive():
    manager = ConversationSessionManager()

    manager.create("conversation-1")

    manager.archive("conversation-1")

    assert manager.get_session(
        "conversation-1"
    )["archived"] is True

    manager.unarchive("conversation-1")

    assert manager.get_session(
        "conversation-1"
    )["archived"] is False


def test_delete_conversation():
    manager = ConversationSessionManager()

    manager.create("conversation-1")

    deleted = manager.delete(
        "conversation-1"
    )

    assert deleted is True

    sessions = manager.list_sessions(
        include_archived=True
    )

    assert sessions == []


def test_delete_missing_conversation():
    manager = ConversationSessionManager()

    deleted = manager.delete(
        "does-not-exist"
    )

    assert deleted is False


def test_get_conversation_returns_messages():
    manager = ConversationSessionManager()

    manager.create(
        "conversation-1",
        title="Revenue Analysis",
    )

    manager.add_message(
        "conversation-1",
        {
            "role": "user",
            "content": "Show revenue",
        },
    )

    conversation = manager.get_conversation(
        "conversation-1"
    )

    assert (
        conversation["title"]
        == "Revenue Analysis"
    )

    assert len(
        conversation["history"]
    ) == 1

    assert (
        conversation["history"][0]["content"]
        == "Show revenue"
    )


def test_get_conversation_returns_defensive_copy():
    manager = ConversationSessionManager()

    manager.create(
        "conversation-1",
        title="Revenue Analysis",
    )

    manager.add_message(
        "conversation-1",
        {
            "role": "user",
            "content": "Show revenue",
        },
    )

    conversation = manager.get_conversation(
        "conversation-1"
    )

    conversation["title"] = "Modified externally"
    conversation["history"][0][
        "content"
    ] = "Modified externally"

    stored_conversation = (
        manager.get_conversation(
            "conversation-1"
        )
    )

    assert (
        stored_conversation["title"]
        == "Revenue Analysis"
    )

    assert (
        stored_conversation["history"][0][
            "content"
        ]
        == "Show revenue"
    )