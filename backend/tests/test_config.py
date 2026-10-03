import pytest
from pydantic import ValidationError

from app.config import Settings


def test_settings_loads_required_and_default_values(
    monkeypatch,
):
    monkeypatch.setenv(
        "GROQ_API_KEY",
        "test-api-key",
    )

    settings = Settings()

    assert (
        settings.groq_api_key.get_secret_value()
        == "test-api-key"
    )
    assert settings.groq_model == "openai/gpt-oss-20b"
    assert settings.max_tool_iterations == 8
    assert settings.app_name == "CPG Analytics Copilot"
    assert settings.app_version == "0.2.0"

    assert settings.cors_origin_list == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


def test_settings_requires_groq_api_key(
    monkeypatch,
):
    monkeypatch.delenv(
        "GROQ_API_KEY",
        raising=False,
    )

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


@pytest.mark.parametrize(
    "value",
    [
        "0",
        "-1",
        "21",
    ],
)
def test_max_tool_iterations_rejects_invalid_values(
    monkeypatch,
    value,
):
    monkeypatch.setenv(
        "GROQ_API_KEY",
        "test-api-key",
    )
    monkeypatch.setenv(
        "MAX_TOOL_ITERATIONS",
        value,
    )

    with pytest.raises(ValidationError):
        Settings()


@pytest.mark.parametrize(
    "value",
    [
        "1",
        "8",
        "20",
    ],
)
def test_max_tool_iterations_accepts_valid_values(
    monkeypatch,
    value,
):
    monkeypatch.setenv(
        "GROQ_API_KEY",
        "test-api-key",
    )
    monkeypatch.setenv(
        "MAX_TOOL_ITERATIONS",
        value,
    )

    settings = Settings()

    assert settings.max_tool_iterations == int(value)


def test_cors_origin_list_strips_whitespace(
    monkeypatch,
):
    monkeypatch.setenv(
        "GROQ_API_KEY",
        "test-api-key",
    )
    monkeypatch.setenv(
        "CORS_ORIGINS",
        (
            " http://localhost:5173, "
            "http://example.com "
        ),
    )

    settings = Settings()

    assert settings.cors_origin_list == [
        "http://localhost:5173",
        "http://example.com",
    ]


def test_cors_origin_list_ignores_empty_entries(
    monkeypatch,
):
    monkeypatch.setenv(
        "GROQ_API_KEY",
        "test-api-key",
    )
    monkeypatch.setenv(
        "CORS_ORIGINS",
        "http://localhost:5173,,",
    )

    settings = Settings()

    assert settings.cors_origin_list == [
        "http://localhost:5173",
    ]


@pytest.mark.parametrize(
    "environment_variable",
    [
        "GROQ_API_KEY",
        "GROQ_MODEL",
        "APP_NAME",
        "APP_VERSION",
    ],
)
def test_required_text_configuration_rejects_blank_values(
    monkeypatch,
    environment_variable,
):
    monkeypatch.setenv(
        "GROQ_API_KEY",
        "test-api-key",
    )

    monkeypatch.setenv(
        environment_variable,
        "   ",
    )

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_cors_origins_rejects_blank_value(
    monkeypatch,
):
    monkeypatch.setenv(
        "GROQ_API_KEY",
        "test-api-key",
    )
    monkeypatch.setenv(
        "CORS_ORIGINS",
        "   ",
    )

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


@pytest.mark.parametrize(
    "cors_origins",
    [
        "localhost:5173",
        "example.com",
        "random-value",
        "ftp://example.com",
    ],
)
def test_cors_origins_reject_invalid_origins(
    monkeypatch,
    cors_origins,
):
    monkeypatch.setenv(
        "GROQ_API_KEY",
        "test-api-key",
    )
    monkeypatch.setenv(
        "CORS_ORIGINS",
        cors_origins,
    )

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


@pytest.mark.parametrize(
    "cors_origins",
    [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://example.com",
        (
            "http://localhost:5173,"
            "https://example.com"
        ),
    ],
)
def test_cors_origins_accept_valid_origins(
    monkeypatch,
    cors_origins,
):
    monkeypatch.setenv(
        "GROQ_API_KEY",
        "test-api-key",
    )
    monkeypatch.setenv(
        "CORS_ORIGINS",
        cors_origins,
    )

    settings = Settings(_env_file=None)

    assert settings.cors_origin_list == [
        origin.strip()
        for origin in cors_origins.split(",")
    ]


def test_settings_repr_does_not_expose_groq_api_key(
    monkeypatch,
):
    monkeypatch.setenv(
        "GROQ_API_KEY",
        "super-secret-test-key",
    )

    settings = Settings(_env_file=None)

    representation = repr(settings)

    assert "super-secret-test-key" not in representation