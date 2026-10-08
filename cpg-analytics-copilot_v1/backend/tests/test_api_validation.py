from pydantic import ValidationError

from app.main import (
    ChatRequest,
    ConversationCreateRequest,
    ConversationRenameRequest,
)


def test_chat_request_rejects_blank_message():
    try:
        ChatRequest(
            message="   ",
            conversation_id="test",
        )
    except ValidationError:
        return

    raise AssertionError(
        "Blank message should raise ValidationError."
    )


def test_chat_request_trims_message():
    request = ChatRequest(
        message="  What is our revenue?  ",
        conversation_id="test",
    )

    assert request.message == (
        "What is our revenue?"
    )


def test_chat_request_trims_conversation_id():
    request = ChatRequest(
        message="What is our revenue?",
        conversation_id="  sales-session  ",
    )

    assert request.conversation_id == (
        "sales-session"
    )


def test_chat_request_rejects_blank_conversation_id():
    try:
        ChatRequest(
            message="What is our revenue?",
            conversation_id="   ",
        )
    except ValidationError:
        return

    raise AssertionError(
        "Blank conversation ID should raise ValidationError."
    )


def test_chat_request_rejects_message_above_max_length():
    try:
        ChatRequest(
            message="x" * 4001,
            conversation_id="test",
        )
    except ValidationError:
        return

    raise AssertionError(
        "Oversized message should raise ValidationError."
    )


def test_create_request_uses_default_title():
    request = ConversationCreateRequest()

    assert request.title == "New Chat"
    assert request.conversation_id is None


def test_create_request_rejects_blank_title():
    try:
        ConversationCreateRequest(
            title="   ",
        )
    except ValidationError:
        return

    raise AssertionError(
        "Blank conversation title should raise ValidationError."
    )


def test_create_request_trims_title():
    request = ConversationCreateRequest(
        title="  Sales Analysis  ",
    )

    assert request.title == "Sales Analysis"


def test_create_request_trims_custom_id():
    request = ConversationCreateRequest(
        conversation_id="  custom-session  ",
        title="Sales Analysis",
    )

    assert request.conversation_id == (
        "custom-session"
    )


def test_rename_request_rejects_blank_title():
    try:
        ConversationRenameRequest(
            title="   ",
        )
    except ValidationError:
        return

    raise AssertionError(
        "Blank rename title should raise ValidationError."
    )


def test_rename_request_trims_title():
    request = ConversationRenameRequest(
        title="  New Title  ",
    )

    assert request.title == "New Title"