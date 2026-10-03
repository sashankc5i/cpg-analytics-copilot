from __future__ import annotations

from contextvars import ContextVar
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class RequestTelemetry:
    request_id: str
    llm_calls: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)

    def summary(self) -> dict[str, Any]:
        total_tokens = sum(
            item.get("total_tokens") or 0
            for item in self.llm_calls
        )
        return {
            "request_id": self.request_id,
            "llm_call_count": len(self.llm_calls),
            "tool_call_count": len(self.tool_calls),
            "total_tokens": total_tokens,
        }


_current_telemetry: ContextVar[RequestTelemetry | None] = ContextVar(
    "current_request_telemetry",
    default=None,
)


def start_request_telemetry(request_id: str) -> RequestTelemetry:
    telemetry = RequestTelemetry(request_id=request_id)
    _current_telemetry.set(telemetry)
    return telemetry


def get_request_telemetry() -> RequestTelemetry | None:
    return _current_telemetry.get()


def clear_request_telemetry() -> None:
    _current_telemetry.set(None)


def record_llm_call(
    *,
    model: str,
    duration_ms: float,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    total_tokens: int | None,
    success: bool,
    retry_count: int = 0,
    error_type: str | None = None,
) -> None:
    telemetry = get_request_telemetry()
    if telemetry is None:
        return

    telemetry.llm_calls.append(
        {
            "model": model,
            "duration_ms": duration_ms,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "success": success,
            "retry_count": retry_count,
            "error_type": error_type,
        }
    )


def record_tool_execution(
    *,
    tool: str,
    duration_ms: float,
    success: bool,
    error_type: str | None = None,
) -> None:
    telemetry = get_request_telemetry()
    if telemetry is None:
        return

    telemetry.tool_calls.append(
        {
            "tool": tool,
            "duration_ms": duration_ms,
            "success": success,
            "error_type": error_type,
        }
    )


def telemetry_to_dict() -> dict[str, Any] | None:
    telemetry = get_request_telemetry()
    if telemetry is None:
        return None
    return asdict(telemetry)
