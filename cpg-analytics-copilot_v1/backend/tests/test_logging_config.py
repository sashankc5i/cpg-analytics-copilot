from types import SimpleNamespace

import pytest

from app.logging_config import (
    get_request_id,
    sanitize_log_message,
)


def test_get_request_id_returns_request_state_id():
    request = SimpleNamespace(
        state=SimpleNamespace(
            request_id="test-request-id",
        ),
    )

    assert (
        get_request_id(request)
        == "test-request-id"
    )


def test_get_request_id_returns_unknown_when_missing():
    request = SimpleNamespace(
        state=SimpleNamespace(),
    )

    assert (
        get_request_id(request)
        == "unknown"
    )


@pytest.mark.parametrize(
    "message,secret",
    [
        (
            "api_key=super-secret-key",
            "super-secret-key",
        ),
        (
            "API-KEY=super-secret-key",
            "super-secret-key",
        ),
        (
            "authorization=Bearer-secret-token",
            "Bearer-secret-token",
        ),
        (
            "password=super-secret-password",
            "super-secret-password",
        ),
        (
            "secret=super-secret-value",
            "super-secret-value",
        ),
        (
            "token=super-secret-token",
            "super-secret-token",
        ),
    ],
)
def test_sanitize_log_message_redacts_sensitive_values(
    message,
    secret,
):
    sanitized = sanitize_log_message(
        message
    )

    assert secret not in sanitized
    assert "[REDACTED]" in sanitized


def test_sanitize_log_message_preserves_safe_content():
    message = (
        "agent_failed | "
        "request_id=abc-123 | "
        "operation=llm_call"
    )

    sanitized = sanitize_log_message(
        message
    )

    assert sanitized == message


def test_sanitize_log_message_handles_non_string_values():
    sanitized = sanitize_log_message(
        12345
    )

    assert sanitized == "12345"