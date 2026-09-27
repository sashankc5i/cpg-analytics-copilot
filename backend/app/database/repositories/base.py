import logging
import sqlite3
from collections.abc import Callable
from typing import Any


logger = logging.getLogger(__name__)


class RepositoryError(RuntimeError):
    """Raised when a repository operation fails."""


def raise_repository_error(
    operation: str,
    error: sqlite3.Error,
) -> None:
    logger.exception(
        "repository_operation_failed | "
        "operation=%s",
        operation,
    )

    raise RepositoryError(
        f"Repository operation failed: {operation}."
    ) from error


def execute_repository_operation(
    operation: str,
    callback: Callable[[], Any],
) -> Any:
    """
    Execute a repository database operation and translate
    database-specific errors into RepositoryError.

    The operation name is logged for observability.
    Raw SQL, parameters, and database contents are never
    logged here.
    """

    logger.info(
        "repository_operation_started | "
        "operation=%s",
        operation,
    )

    try:
        result = callback()

        logger.info(
            "repository_operation_completed | "
            "operation=%s",
            operation,
        )

        return result

    except sqlite3.Error as error:
        raise_repository_error(
            operation,
            error,
        )