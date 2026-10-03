import logging
import re
import sys
from typing import Any

from fastapi import Request


LOG_FORMAT = (
    "%(asctime)s | "
    "%(levelname)s | "
    "%(name)s | "
    "%(message)s"
)


_SENSITIVE_PATTERNS = [
    re.compile(
        r"(api[_-]?key\s*[=:]\s*)([^,\s|]+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(authorization\s*[=:]\s*)([^,\s|]+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(bearer\s+)([^,\s|]+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(password\s*[=:]\s*)([^,\s|]+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(secret\s*[=:]\s*)([^,\s|]+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(token\s*[=:]\s*)([^,\s|]+)",
        re.IGNORECASE,
    ),
]


def configure_logging() -> None:
    """
    Configure application-wide logging.

    Logs are written to stdout so they can be collected
    naturally by container platforms and centralized logging
    systems.

    force=True ensures the application controls the root
    logging configuration even when another library has
    configured logging before application startup.
    """

    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )


def get_logger(name: str) -> logging.Logger:
    """
    Return a named application logger.

    Using module-specific loggers keeps log records
    attributable to the component that produced them.
    """

    return logging.getLogger(name)


def get_request_id(
    request: Request,
) -> str:
    """
    Return the request correlation ID stored by the
    request logging middleware.

    A fallback value is returned when this helper is used
    outside a normal HTTP request lifecycle.
    """

    return getattr(
        request.state,
        "request_id",
        "unknown",
    )


def sanitize_log_message(
    message: str,
) -> str:
    """
    Remove common secret-like values from a log message.

    This is a defensive final layer for messages that may
    contain unexpected sensitive values.

    Application code should still avoid logging secrets
    explicitly. Sanitization is not a replacement for
    careful logging.
    """

    if not isinstance(message, str):
        message = str(message)

    sanitized = message

    for pattern in _SENSITIVE_PATTERNS:
        sanitized = pattern.sub(
            r"\1[REDACTED]",
            sanitized,
        )

    return sanitized

def log_event(
    logger: logging.Logger,
    event: str,
    **fields: Any,
) -> None:
    """Emit a compact structured application log event.

    Values are sanitized before logging so operational telemetry does not
    accidentally expose common secret-like values.
    """

    parts = [event]

    for key, value in fields.items():
        parts.append(
            sanitize_log_message(
                f"{key}={value}"
            )
        )

    logger.info(" | ".join(parts))
