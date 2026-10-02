import logging
import re
import time
from collections.abc import Callable
from typing import Any

from groq import (
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
)

from app.config import get_settings


logger = logging.getLogger(__name__)


# ============================================================
# Retry configuration
# ============================================================

DEFAULT_MAX_RETRIES = 2
DEFAULT_RETRY_BASE_DELAY_SECONDS = 0.5
RETRY_SAFETY_BUFFER_SECONDS = 1.0

RETRYABLE_STATUS_CODES = {
    408,
    429,
    500,
    502,
    503,
    504,
}


# ============================================================
# Configuration helpers
# ============================================================

def _get_retry_count() -> int:
    """
    Return the application retry count.

    The retry policy intentionally uses safe defaults when
    retry-specific settings are not present in Settings.

    This keeps the retry layer backward compatible with the
    current configuration model.
    """

    settings = get_settings()

    value = getattr(
        settings,
        "groq_max_retries",
        DEFAULT_MAX_RETRIES,
    )

    try:
        value = int(value)
    except (TypeError, ValueError):
        value = DEFAULT_MAX_RETRIES

    return max(
        0,
        value,
    )


def _get_retry_base_delay() -> float:
    """
    Return the base delay used for exponential backoff.

    Retry-specific configuration is optional. The current
    application configuration does not define it, so the
    retry layer falls back to a safe default.
    """

    settings = get_settings()

    value = getattr(
        settings,
        "groq_retry_base_delay_seconds",
        DEFAULT_RETRY_BASE_DELAY_SECONDS,
    )

    try:
        value = float(value)
    except (TypeError, ValueError):
        value = DEFAULT_RETRY_BASE_DELAY_SECONDS

    return max(
        0.0,
        value,
    )


# ============================================================
# Exception helpers
# ============================================================

def _get_status_code(
    error: Exception,
) -> int | None:
    """
    Extract an HTTP status code from a provider exception.
    """

    status_code = getattr(
        error,
        "status_code",
        None,
    )

    if status_code is None:
        response = getattr(
            error,
            "response",
            None,
        )

        status_code = getattr(
            response,
            "status_code",
            None,
        )

    try:
        if status_code is not None:
            return int(status_code)
    except (TypeError, ValueError):
        return None

    return None


def _is_retryable(
    error: Exception,
) -> bool:
    """
    Determine whether an exception represents a transient
    failure that should be retried.
    """

    if isinstance(
        error,
        (
            APIConnectionError,
            APITimeoutError,
            RateLimitError,
        ),
    ):
        return True

    status_code = _get_status_code(error)

    return status_code in RETRYABLE_STATUS_CODES


# ============================================================
# Provider retry-delay extraction
# ============================================================

def _get_retry_after_from_headers(
    error: Exception,
) -> float | None:
    """
    Extract Retry-After from an HTTP response when available.
    """

    response = getattr(
        error,
        "response",
        None,
    )

    if response is None:
        return None

    headers = getattr(
        response,
        "headers",
        None,
    )

    if headers is None:
        return None

    try:
        value = headers.get(
            "retry-after"
        )

        if value is None:
            value = headers.get(
                "Retry-After"
            )

        if value is None:
            return None

        return max(
            0.0,
            float(value),
        )

    except (
        TypeError,
        ValueError,
    ):
        return None


def _get_retry_delay_from_message(
    error: Exception,
) -> float | None:
    """
    Extract provider-requested retry delay from an error
    message.

    Example:

        Please try again in 6.795s.
    """

    message = str(error)

    match = re.search(
        r"try again in\s+"
        r"([0-9]+(?:\.[0-9]+)?)"
        r"\s*(?:s|sec|secs|seconds)",
        message,
        flags=re.IGNORECASE,
    )

    if not match:
        return None

    try:
        return max(
            0.0,
            float(match.group(1)),
        )
    except ValueError:
        return None


def _get_retry_delay(
    error: Exception,
    retry_number: int,
) -> float:
    """
    Determine how long to wait before the next attempt.

    Priority:

    1. Retry-After HTTP header
    2. Provider message retry delay
    3. Exponential backoff
    """

    retry_after = _get_retry_after_from_headers(
        error
    )

    if retry_after is not None:
        return (
            retry_after
            + RETRY_SAFETY_BUFFER_SECONDS
        )

    provider_delay = _get_retry_delay_from_message(
        error
    )

    if provider_delay is not None:
        return (
            provider_delay
            + RETRY_SAFETY_BUFFER_SECONDS
        )

    base_delay = _get_retry_base_delay()

    return (
        base_delay
        * (2 ** retry_number)
    )


# ============================================================
# Retry execution
# ============================================================

def execute_with_retry(
    operation: Callable[[], Any],
    *,
    operation_name: str = "operation",
):
    """
    Execute an operation using the application's common
    transient-failure retry policy.

    Non-retryable exceptions are raised immediately.

    Retryable exceptions are retried up to the configured
    retry count.

    The final exception is allowed to propagate to the caller.
    """

    max_retries = _get_retry_count()

    attempt = 0

    while True:

        try:
            return operation()

        except Exception as error:

            if not _is_retryable(error):
                logger.debug(
                    "retry_not_applicable | "
                    "operation=%s | "
                    "error_type=%s",
                    operation_name,
                    type(error).__name__,
                )

                raise

            if attempt >= max_retries:

                logger.warning(
                    "retry_exhausted | "
                    "operation=%s | "
                    "attempts=%s | "
                    "error_type=%s",
                    operation_name,
                    attempt + 1,
                    type(error).__name__,
                )

                raise

            delay = _get_retry_delay(
                error,
                attempt,
            )

            logger.warning(
                "retry_scheduled | "
                "operation=%s | "
                "attempt=%s/%s | "
                "delay=%.2fs | "
                "error_type=%s | "
                "status_code=%s",
                operation_name,
                attempt + 1,
                max_retries,
                delay,
                type(error).__name__,
                _get_status_code(error),
            )

            time.sleep(delay)

            attempt += 1