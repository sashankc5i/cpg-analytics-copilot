from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central application configuration.

    Values are loaded from environment variables and,
    during local development, from the backend/.env file.
    """

    groq_api_key: str = Field(
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