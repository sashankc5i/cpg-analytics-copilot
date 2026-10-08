import time
import uuid

from fastapi import Request

from app.logging_config import (
    get_logger,
)


logger = get_logger(__name__)


async def request_logging_middleware(
    request: Request,
    call_next,
):
    """
    Add a request correlation ID and log the lifecycle
    of every HTTP request.

    The request ID is stored on request.state so downstream
    endpoints can include the same ID in their logs and
    responses.
    """

    request_id = str(uuid.uuid4())

    request.state.request_id = request_id

    start_time = time.perf_counter()

    logger.info(
        "request_started | "
        "request_id=%s | "
        "method=%s | "
        "path=%s",
        request_id,
        request.method,
        request.url.path,
    )

    try:
        response = await call_next(request)

        duration_ms = round(
            (time.perf_counter() - start_time) * 1000,
            2,
        )

        response.headers["X-Request-ID"] = request_id

        logger.info(
            "request_completed | "
            "request_id=%s | "
            "status=%s | "
            "duration_ms=%s",
            request_id,
            response.status_code,
            duration_ms,
        )

        return response

    except Exception:
        duration_ms = round(
            (time.perf_counter() - start_time) * 1000,
            2,
        )

        logger.exception(
            "request_failed | "
            "request_id=%s | "
            "duration_ms=%s",
            request_id,
            duration_ms,
        )

        raise