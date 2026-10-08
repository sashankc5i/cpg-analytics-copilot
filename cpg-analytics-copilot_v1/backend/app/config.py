from functools import lru_cache
from urllib.parse import urlparse

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _validate_non_blank_text(
    value: str,
    field_name: str,
) -> str:
    """
    Validate that a configuration text value is not blank.

    Leading and trailing whitespace is removed so configuration
    values are normalized before the application uses them.
    """

    if not isinstance(value, str):
        raise ValueError(
            f"{field_name} must be a string."
        )

    value = value.strip()

    if not value:
        raise ValueError(
            f"{field_name} must not be blank."
        )

    return value


def _validate_cors_origin(
    origin: str,
) -> str:
    """
    Validate a single HTTP/HTTPS CORS origin.
    """

    origin = origin.strip()

    parsed = urlparse(origin)

    if parsed.scheme not in {"http", "https"}:
        raise ValueError(
            "CORS origins must use http or https."
        )

    if not parsed.hostname:
        raise ValueError(
            "CORS origins must contain a hostname."
        )

    if (
        parsed.path
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(
            "CORS origins must not contain a path, "
            "query, or fragment."
        )

    return origin


class Settings(BaseSettings):
    """
    Central application configuration.

    Values are loaded from environment variables and,
    during local development, from the backend/.env file.
    """

    groq_api_key: SecretStr = Field(
        ...,
        alias="GROQ_API_KEY",
    )

    groq_model: str = Field(
        default="openai/gpt-oss-20b",
        alias="GROQ_MODEL",
    )

    max_tool_iterations: int = Field(
        default=8,
        alias="MAX_TOOL_ITERATIONS",
        ge=1,
        le=20,
    )

    cors_origins: str = Field(
        default=(
            "http://localhost:5173,"
            "http://127.0.0.1:5173"
        ),
        alias="CORS_ORIGINS",
    )

    app_name: str = Field(
        default="CPG Analytics Copilot",
        alias="APP_NAME",
    )

    app_version: str = Field(
        default="0.1.0",
        alias="APP_VERSION",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator(
        "groq_api_key",
        "groq_model",
        "app_name",
        "app_version",
        mode="before",
    )
    @classmethod
    def validate_text_configuration(
        cls,
        value,
        info,
    ):
        """
        Validate text-based configuration values.

        GROQ_API_KEY is handled as SecretStr by Pydantic
        after the raw environment value passes this validator.
        """

        if info.field_name == "groq_api_key":
            if not isinstance(value, str):
                raise ValueError(
                    "groq_api_key must be a string."
                )

            value = value.strip()

            if not value:
                raise ValueError(
                    "groq_api_key must not be blank."
                )

            return value

        return _validate_non_blank_text(
            value,
            info.field_name,
        )

    @field_validator(
        "cors_origins",
        mode="before",
    )
    @classmethod
    def validate_cors_origins(
        cls,
        value: str,
    ) -> str:
        value = _validate_non_blank_text(
            value,
            "cors_origins",
        )

        origins = [
            origin.strip()
            for origin in value.split(",")
            if origin.strip()
        ]

        if not origins:
            raise ValueError(
                "cors_origins must contain at least "
                "one origin."
            )

        for origin in origins:
            _validate_cors_origin(origin)

        return ",".join(origins)

    @property
    def cors_origin_list(self) -> list[str]:
        """
        Convert the comma-separated CORS configuration
        into a list suitable for FastAPI middleware.
        """

        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    """
    Return a cached application settings instance.

    Caching ensures configuration is loaded once and
    reused throughout the application lifecycle.
    """

    return Settings()