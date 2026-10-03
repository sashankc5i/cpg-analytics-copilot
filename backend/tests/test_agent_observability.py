from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.agent.agent import AnalyticsAgent
from app.observability.telemetry import (
    clear_request_telemetry,
    get_request_telemetry,
    start_request_telemetry,
)


def _message(*, content=None, tool_calls=None):
    return SimpleNamespace(
        content=content,
        tool_calls=tool_calls or [],
    )


def _tool_call(name="get_overall_sales"):
    return SimpleNamespace(
        id="tool-call-1",
        function=SimpleNamespace(
            name=name,
            arguments="{}",
        ),
    )


def setup_function():
    clear_request_telemetry()


def teardown_function():
    clear_request_telemetry()


def test_llm_call_records_provider_token_usage():
    with patch.dict(
        "os.environ",
        {"GROQ_API_KEY": "test-key"},
    ):
        agent = AnalyticsAgent()

    response = MagicMock()
    response.usage.prompt_tokens = 150
    response.usage.completion_tokens = 35
    response.usage.total_tokens = 185
    response.choices = [
        SimpleNamespace(
            message=_message(content="Revenue is stable."),
        )
    ]

    agent.client.chat.completions.create = MagicMock(
        return_value=response
    )

    start_request_telemetry("request-llm")

    agent._call_llm([
        {"role": "user", "content": "Revenue?"},
    ])

    telemetry = get_request_telemetry()

    assert telemetry is not None
    assert len(telemetry.llm_calls) == 1
    assert telemetry.llm_calls[0]["prompt_tokens"] == 150
    assert telemetry.llm_calls[0]["completion_tokens"] == 35
    assert telemetry.llm_calls[0]["total_tokens"] == 185
    assert telemetry.llm_calls[0]["success"] is True


def test_agent_records_tool_execution_telemetry_without_api_call():
    with patch.dict(
        "os.environ",
        {"GROQ_API_KEY": "test-key"},
    ):
        agent = AnalyticsAgent()

    first_response = MagicMock()
    first_response.usage.prompt_tokens = 100
    first_response.usage.completion_tokens = 10
    first_response.usage.total_tokens = 110
    first_response.choices = [
        SimpleNamespace(
            message=_message(
                content=None,
                tool_calls=[_tool_call()],
            ),
        )
    ]

    final_response = MagicMock()
    final_response.usage.prompt_tokens = 200
    final_response.usage.completion_tokens = 20
    final_response.usage.total_tokens = 220
    final_response.choices = [
        SimpleNamespace(
            message=_message(
                content="Revenue is $100.",
            ),
        )
    ]

    agent.client.chat.completions.create = MagicMock(
        side_effect=[
            first_response,
            final_response,
        ]
    )

    with patch(
        "app.agent.agent.execute_tool_as_json",
        return_value='{"revenue": 100}',
    ):
        start_request_telemetry("request-tool")

        result = agent.run(
            user_message="What is revenue?",
            history=[],
        )

    telemetry = get_request_telemetry()

    assert result["answer"] == "Revenue is $100."
    assert telemetry is not None
    assert len(telemetry.tool_calls) == 1
    assert telemetry.tool_calls[0]["tool"] == "get_overall_sales"
    assert telemetry.tool_calls[0]["success"] is True
    assert telemetry.summary()["llm_call_count"] == 2
    assert telemetry.summary()["tool_call_count"] == 1
    assert telemetry.summary()["total_tokens"] == 330
