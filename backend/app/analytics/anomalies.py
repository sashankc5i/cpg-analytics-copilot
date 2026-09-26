from app.database.repositories.sales_repository import (
    get_monthly_revenue_data,
)


MIN_HISTORY_MONTHS = 3

LOW_ANOMALY_THRESHOLD = 10.0
MEDIUM_ANOMALY_THRESHOLD = 20.0
HIGH_ANOMALY_THRESHOLD = 30.0


def _calculate_severity(
    deviation_percentage: float,
) -> str:
    deviation = abs(deviation_percentage)

    if deviation < LOW_ANOMALY_THRESHOLD:
        return "normal"

    if deviation < MEDIUM_ANOMALY_THRESHOLD:
        return "low"

    if deviation < HIGH_ANOMALY_THRESHOLD:
        return "medium"

    return "high"


def _calculate_direction(
    deviation_percentage: float,
) -> str:
    if deviation_percentage > 0:
        return "up"

    if deviation_percentage < 0:
        return "down"

    return "flat"


def detect_revenue_anomalies(
    monthly_revenue: list[dict],
) -> list[dict]:
    anomalies = []

    for index, current in enumerate(monthly_revenue):

        if index < MIN_HISTORY_MONTHS:
            continue

        historical_values = [
            item["actual_revenue"]
            for item in monthly_revenue[
                index - MIN_HISTORY_MONTHS:index
            ]
        ]

        expected_revenue = (
            sum(historical_values)
            / len(historical_values)
        )

        actual_revenue = current["actual_revenue"]

        if expected_revenue == 0:
            continue

        deviation_percentage = (
            (actual_revenue - expected_revenue)
            / expected_revenue
        ) * 100

        deviation_percentage = round(
            deviation_percentage,
            2,
        )

        severity = _calculate_severity(
            deviation_percentage
        )

        if severity == "normal":
            continue

        anomalies.append(
            {
                "period": current["period"],
                "actual_revenue": round(
                    actual_revenue,
                    2,
                ),
                "expected_revenue": round(
                    expected_revenue,
                    2,
                ),
                "deviation_percentage": (
                    deviation_percentage
                ),
                "direction": _calculate_direction(
                    deviation_percentage
                ),
                "severity": severity,
            }
        )

    return anomalies


def get_revenue_anomalies() -> list[dict]:
    monthly_revenue = get_monthly_revenue_data()

    return detect_revenue_anomalies(
        monthly_revenue
    )