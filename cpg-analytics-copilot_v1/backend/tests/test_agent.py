from unittest.mock import MagicMock, patch

import pytest

from app.agent.agent import AnalyticsAgent


def test_agent_initialization():

    with patch.dict(
        "os.environ",
        {"GROQ_API_KEY": "test-key"},
    ):

        agent = AnalyticsAgent()

        assert agent.model == "openai/gpt-oss-20b"


def test_agent_returns_final_answer():

    with patch.dict(
        "os.environ",
        {"GROQ_API_KEY": "test-key"},
    ):

        agent = AnalyticsAgent()

        mock_response = MagicMock()

        mock_response.choices[0].message.tool_calls = None

        mock_response.choices[0].message.content = (
            "Total revenue is ₹100 million."
        )

        agent.client.chat.completions.create = MagicMock(
            return_value=mock_response
        )

        result = agent.run(
            "What is our total revenue?"
        )

        assert result["answer"] == (
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
            agent.run(
                "What is our total revenue?"
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
            agent.run(
                "What is our total revenue?"
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
            agent.run(
                "What is our total revenue?"
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
            agent.run(
                "What is our total revenue?"
            )


def test_agent_rejects_empty_final_answer():

    with patch.dict(
        "os.environ",
        {"GROQ_API_KEY": "test-key"},
    ):

        agent = AnalyticsAgent()

        mock_response = MagicMock()

        mock_response.choices[0].message.tool_calls = None

        mock_response.choices[0].message.content = "   "

        agent.client.chat.completions.create = MagicMock(
            return_value=mock_response
        )

        with pytest.raises(
            RuntimeError,
            match="analytics model returned an empty answer",
        ):
            agent.run(
                "What is our total revenue?"
            )


def test_agent_rejects_non_string_final_answer():

    with patch.dict(
        "os.environ",
        {"GROQ_API_KEY": "test-key"},
    ):

        agent = AnalyticsAgent()

        mock_response = MagicMock()

        mock_response.choices[0].message.tool_calls = None

        mock_response.choices[0].message.content = None

        agent.client.chat.completions.create = MagicMock(
            return_value=mock_response
        )

        with pytest.raises(
            RuntimeError,
            match="analytics model returned an invalid answer",
        ):
            agent.run(
                "What is our total revenue?"
            )