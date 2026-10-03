from app.observability.telemetry import (
    clear_request_telemetry,
    get_request_telemetry,
    record_llm_call,
    record_tool_execution,
    start_request_telemetry,
)


def setup_function():
    clear_request_telemetry()


def teardown_function():
    clear_request_telemetry()


def test_request_telemetry_tracks_request_id_and_summary():
    start_request_telemetry("request-123")

    record_llm_call(
        model="test-model",
        duration_ms=42.5,
        prompt_tokens=100,
        completion_tokens=20,
        total_tokens=120,
        success=True,
    )

    record_tool_execution(
        tool="get_overall_sales",
        duration_ms=8.2,
        success=True,
    )

    telemetry = get_request_telemetry()

    assert telemetry is not None
    assert telemetry.request_id == "request-123"
    assert telemetry.summary() == {
        "request_id": "request-123",
        "llm_call_count": 1,
        "tool_call_count": 1,
        "total_tokens": 120,
    }


def test_failed_calls_are_recorded_without_result_payloads():
    start_request_telemetry("request-456")

    record_llm_call(
        model="test-model",
        duration_ms=12.0,
        prompt_tokens=None,
        completion_tokens=None,
        total_tokens=None,
        success=False,
        retry_count=2,
        error_type="RateLimitError",
    )

    record_tool_execution(
        tool="get_sales_by_region",
        duration_ms=3.0,
        success=False,
        error_type="ValueError",
    )

    telemetry = get_request_telemetry()

    assert telemetry is not None
    assert telemetry.llm_calls[0]["success"] is False
    assert telemetry.llm_calls[0]["retry_count"] == 2
    assert telemetry.llm_calls[0]["error_type"] == "RateLimitError"
    assert telemetry.tool_calls[0]["success"] is False
    assert telemetry.tool_calls[0]["error_type"] == "ValueError"
    assert "result" not in telemetry.tool_calls[0]
