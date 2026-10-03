from unittest.mock import MagicMock, patch

import pytest

from app.agent.agent import AnalyticsAgent


class FakeRateLimitError(Exception):
    """
    Lightweight test exception used to simulate Groq RateLimitError.

    The production agent catches RateLimitError, so the test patches
    that class inside app.agent.agent with this test exception.
    """


# ----------------------------------------------------------------------
# Initialization
# ----------------------------------------------------------------------


def test_agent_initialization():
    with patch.dict(
        "os.environ",
        {"GROQ_API_KEY": "test-key"},
    ):
        agent = AnalyticsAgent()

        assert agent.model == "openai/gpt-oss-20b"


# ----------------------------------------------------------------------
# LLM response handling
# ----------------------------------------------------------------------


def test_agent_returns_final_answer():
    with patch.dict(
        "os.environ",
        {"GROQ_API_KEY": "test-key"},
    ):
        agent = AnalyticsAgent()

        mock_response = MagicMock()

        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    tool_calls=None,
                    content="Total revenue is ₹100 million.",
                )
            )
        ]

        agent.client.chat.completions.create = MagicMock(
            return_value=mock_response
        )

        assistant_message = agent._call_llm(
            [
                {
                    "role": "user",
                    "content": "What is our total revenue?",
                }
            ]
        )

        answer = agent._validate_final_answer(
            assistant_message
        )

        assert answer == (
            "Total revenue is ₹100 million."
        )


def test_agent_converts_llm_exception_to_runtime_error():
    with patch.dict(
        "os.environ",
        {"GROQ_API_KEY": "test-key"},
    ):
        agent = AnalyticsAgent()

        agent.client.chat.completions.create = MagicMock(
            side_effect=Exception(
                "Groq connection failed"
            )
        )

        with pytest.raises(
            RuntimeError,
            match="analytics model could not be reached",
        ):
            agent._call_llm(
                [
                    {
                        "role": "user",
                        "content": "What is our total revenue?",
                    }
                ]
            )


def test_agent_rejects_empty_llm_response():
    with patch.dict(
        "os.environ",
        {"GROQ_API_KEY": "test-key"},
    ):
        agent = AnalyticsAgent()

        agent.client.chat.completions.create = MagicMock(
            return_value=None
        )

        with pytest.raises(
            RuntimeError,
            match="analytics model returned an empty response",
        ):
            agent._call_llm(
                [
                    {
                        "role": "user",
                        "content": "What is our total revenue?",
                    }
                ]
            )


def test_agent_rejects_response_without_choices():
    with patch.dict(
        "os.environ",
        {"GROQ_API_KEY": "test-key"},
    ):
        agent = AnalyticsAgent()

        mock_response = MagicMock()
        mock_response.choices = []

        agent.client.chat.completions.create = MagicMock(
            return_value=mock_response
        )

        with pytest.raises(
            RuntimeError,
            match="analytics model returned an invalid response",
        ):
            agent._call_llm(
                [
                    {
                        "role": "user",
                        "content": "What is our total revenue?",
                    }
                ]
            )


def test_agent_rejects_response_without_message():
    with patch.dict(
        "os.environ",
        {"GROQ_API_KEY": "test-key"},
    ):
        agent = AnalyticsAgent()

        mock_response = MagicMock()

        mock_response.choices = [
            MagicMock(
                message=None
            )
        ]

        agent.client.chat.completions.create = MagicMock(
            return_value=mock_response
        )

        with pytest.raises(
            RuntimeError,
            match="analytics model returned an invalid message",
        ):
            agent._call_llm(
                [
                    {
                        "role": "user",
                        "content": "What is our total revenue?",
                    }
                ]
            )


def test_agent_rejects_empty_final_answer():
    with patch.dict(
        "os.environ",
        {"GROQ_API_KEY": "test-key"},
    ):
        agent = AnalyticsAgent()

        assistant_message = MagicMock()

        assistant_message.content = "   "

        with pytest.raises(
            RuntimeError,
            match="analytics model returned an empty answer",
        ):
            agent._validate_final_answer(
                assistant_message
            )


def test_agent_rejects_non_string_final_answer():
    with patch.dict(
        "os.environ",
        {"GROQ_API_KEY": "test-key"},
    ):
        agent = AnalyticsAgent()

        assistant_message = MagicMock()

        assistant_message.content = None

        with pytest.raises(
            RuntimeError,
            match="analytics model returned an invalid answer",
        ):
            agent._validate_final_answer(
                assistant_message
            )


# ----------------------------------------------------------------------
# Rate-limit tests
# ----------------------------------------------------------------------


def test_agent_retries_temporary_rate_limit():
    with patch.dict(
        "os.environ",
        {"GROQ_API_KEY": "test-key"},
    ):
        agent = AnalyticsAgent()

        mock_response = MagicMock()

        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    tool_calls=None,
                    content="Total revenue is ₹100 million.",
                )
            )
        ]

        agent.client.chat.completions.create = MagicMock(
            side_effect=[
                FakeRateLimitError(
                    "Rate limit reached. "
                    "Please try again in 1s."
                ),
                mock_response,
            ]
        )

        with patch(
            "app.agent.agent.RateLimitError",
            FakeRateLimitError,
        ), patch(
            "app.agent.agent.time.sleep"
        ) as mock_sleep:

            assistant_message = agent._call_llm(
                [
                    {
                        "role": "user",
                        "content": "What is our total revenue?",
                    }
                ]
            )

        answer = agent._validate_final_answer(
            assistant_message
        )

        assert answer == (
            "Total revenue is ₹100 million."
        )

        assert (
            agent.client.chat.completions.create.call_count
            == 2
        )

        mock_sleep.assert_called_once_with(1.0)


def test_agent_fails_fast_on_daily_token_limit():
    with patch.dict(
        "os.environ",
        {"GROQ_API_KEY": "test-key"},
    ):
        agent = AnalyticsAgent()

        agent.client.chat.completions.create = MagicMock(
            side_effect=FakeRateLimitError(
                "Rate limit reached for model. "
                "TPD limit: 200000, "
                "Used: 198949, "
                "Requested: 3452. "
                "Please try again in 17m17s."
            )
        )

        with patch(
            "app.agent.agent.RateLimitError",
            FakeRateLimitError,
        ), patch(
            "app.agent.agent.time.sleep"
        ) as mock_sleep:

            with pytest.raises(
                RuntimeError,
                match="daily token limit",
            ):
                agent._call_llm(
                    [
                        {
                            "role": "user",
                            "content": "What is our total revenue?",
                        }
                    ]
                )

        assert (
            agent.client.chat.completions.create.call_count
            == 1
        )

        mock_sleep.assert_not_called()


def test_agent_exhausts_temporary_rate_limit_retries():
    with patch.dict(
        "os.environ",
        {"GROQ_API_KEY": "test-key"},
    ):
        agent = AnalyticsAgent()

        agent.client.chat.completions.create = MagicMock(
            side_effect=FakeRateLimitError(
                "Rate limit reached. "
                "Please try again in 1s."
            )
        )

        with patch(
            "app.agent.agent.RateLimitError",
            FakeRateLimitError,
        ), patch(
            "app.agent.agent.time.sleep"
        ) as mock_sleep:

            with pytest.raises(
                RuntimeError,
                match="temporarily rate-limited",
            ):
                agent._call_llm(
                    [
                        {
                            "role": "user",
                            "content": "What is our total revenue?",
                        }
                    ]
                )

        # MAX_RATE_LIMIT_RETRIES = 3
        #
        # Initial attempt
        # + 3 retries
        # = 4 provider calls
        assert (
            agent.client.chat.completions.create.call_count
            == 4
        )

        assert mock_sleep.call_count == 3


# ----------------------------------------------------------------------
# Clarification / agent orchestration
# ----------------------------------------------------------------------


def test_agent_clarifies_ambiguous_sales_question():
    with patch.dict(
        "os.environ",
        {"GROQ_API_KEY": "test-key"},
    ):
        agent = AnalyticsAgent()

        agent.client.chat.completions.create = MagicMock()

        result = agent.run(
            "How did sales perform?"
        )

        assert result is not None

        assert result["tools_used"] == []
        assert result["tool_results"] == []

        assert (
            "period"
            in result["answer"].lower()
        )

        agent.client.chat.completions.create.assert_not_called()


def test_agent_does_not_clarify_specific_revenue_question():
    with patch.dict(
        "os.environ",
        {"GROQ_API_KEY": "test-key"},
    ):
        agent = AnalyticsAgent()

        mock_response = MagicMock()

        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    tool_calls=None,
                    content=(
                        "Total revenue is "
                        "$298,478,847.26."
                    ),
                )
            )
        ]

        agent.client.chat.completions.create = MagicMock(
            return_value=mock_response
        )

        result = agent.run(
            "What is our total revenue?"
        )

        assert result is not None

        assert (
            result["answer"]
            == "Total revenue is $298,478,847.26."
        )

        agent.client.chat.completions.create.assert_called_once()