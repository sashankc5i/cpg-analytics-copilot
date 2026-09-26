import pytest

from app.agent.agent import AnalyticsAgent


@pytest.mark.live
def test_revenue_anomaly_question_uses_anomaly_tool():
    agent = AnalyticsAgent()

    result = agent.run(
        "Did anything unusual happen to revenue?"
    )

    assert result["answer"]
    assert "get_revenue_anomalies" in result["tools_used"]

    # The current synthetic dataset is intentionally stable,
    # so the anomaly engine should return no significant anomalies.
    anomaly_results = [
        item
        for item in result["tool_results"]
        if item["tool"] == "get_revenue_anomalies"
    ]

    assert len(anomaly_results) == 1
    assert anomaly_results[0]["result"] == []