from app.analytics.anomalies import (
    detect_revenue_anomalies,
)


def test_no_anomaly_for_stable_revenue():
    monthly_revenue = [
        {
            "period": "2026-01",
            "actual_revenue": 1000000,
        },
        {
            "period": "2026-02",
            "actual_revenue": 1010000,
        },
        {
            "period": "2026-03",
            "actual_revenue": 990000,
        },
        {
            "period": "2026-04",
            "actual_revenue": 1005000,
        },
    ]

    result = detect_revenue_anomalies(
        monthly_revenue
    )

    assert result == []


def test_detects_high_negative_anomaly():
    monthly_revenue = [
        {
            "period": "2026-01",
            "actual_revenue": 32000000,
        },
        {
            "period": "2026-02",
            "actual_revenue": 33000000,
        },
        {
            "period": "2026-03",
            "actual_revenue": 32000000,
        },
        {
            "period": "2026-04",
            "actual_revenue": 20000000,
        },
    ]

    result = detect_revenue_anomalies(
        monthly_revenue
    )

    assert len(result) == 1

    anomaly = result[0]

    assert anomaly["period"] == "2026-04"
    assert anomaly["actual_revenue"] == 20000000
    assert anomaly["expected_revenue"] == 32333333.33
    assert anomaly["deviation_percentage"] == -38.14
    assert anomaly["direction"] == "down"
    assert anomaly["severity"] == "high"


def test_detects_high_positive_anomaly():
    monthly_revenue = [
        {
            "period": "2026-01",
            "actual_revenue": 1000000,
        },
        {
            "period": "2026-02",
            "actual_revenue": 1000000,
        },
        {
            "period": "2026-03",
            "actual_revenue": 1000000,
        },
        {
            "period": "2026-04",
            "actual_revenue": 1500000,
        },
    ]

    result = detect_revenue_anomalies(
        monthly_revenue
    )

    assert len(result) == 1

    anomaly = result[0]

    assert anomaly["period"] == "2026-04"
    assert anomaly["actual_revenue"] == 1500000
    assert anomaly["expected_revenue"] == 1000000
    assert anomaly["deviation_percentage"] == 50.0
    assert anomaly["direction"] == "up"
    assert anomaly["severity"] == "high"


def test_requires_minimum_history():
    monthly_revenue = [
        {
            "period": "2026-01",
            "actual_revenue": 1000000,
        },
        {
            "period": "2026-02",
            "actual_revenue": 500000,
        },
        {
            "period": "2026-03",
            "actual_revenue": 500000,
        },
    ]

    result = detect_revenue_anomalies(
        monthly_revenue
    )

    assert result == []


def test_normal_deviation_is_not_returned():
    monthly_revenue = [
        {
            "period": "2026-01",
            "actual_revenue": 1000000,
        },
        {
            "period": "2026-02",
            "actual_revenue": 1000000,
        },
        {
            "period": "2026-03",
            "actual_revenue": 1000000,
        },
        {
            "period": "2026-04",
            "actual_revenue": 1050000,
        },
    ]

    result = detect_revenue_anomalies(
        monthly_revenue
    )

    assert result == []


def test_multiple_anomalies_are_detected():
    monthly_revenue = [
        {
            "period": "2026-01",
            "actual_revenue": 1000000,
        },
        {
            "period": "2026-02",
            "actual_revenue": 1000000,
        },
        {
            "period": "2026-03",
            "actual_revenue": 1000000,
        },
        {
            "period": "2026-04",
            "actual_revenue": 500000,
        },
        {
            "period": "2026-05",
            "actual_revenue": 1000000,
        },
        {
            "period": "2026-06",
            "actual_revenue": 2000000,
        },
    ]

    result = detect_revenue_anomalies(
        monthly_revenue
    )

    assert len(result) == 3

    assert result[0]["period"] == "2026-04"
    assert result[0]["direction"] == "down"

    assert result[1]["period"] == "2026-05"
    assert result[1]["direction"] == "up"
    assert result[1]["severity"] == "medium"

    assert result[2]["period"] == "2026-06"
    assert result[2]["direction"] == "up"


def test_zero_baseline_is_skipped():
    monthly_revenue = [
        {
            "period": "2026-01",
            "actual_revenue": 0,
        },
        {
            "period": "2026-02",
            "actual_revenue": 0,
        },
        {
            "period": "2026-03",
            "actual_revenue": 0,
        },
        {
            "period": "2026-04",
            "actual_revenue": 100000,
        },
    ]

    result = detect_revenue_anomalies(
        monthly_revenue
    )

    assert result == []