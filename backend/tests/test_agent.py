from unittest.mock import MagicMock, patch

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