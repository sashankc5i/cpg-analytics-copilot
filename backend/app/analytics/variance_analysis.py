from copy import deepcopy

from app.analytics.comparison import (
    resolve_comparison_period,
)
from app.analytics.filters import normalize_filters
from app.analytics.metrics import get_metric
from app.analytics.periods import (
    get_latest_available_month,
)
from app.analytics.sales import get_overall_sales
from app.analytics.variance import calculate_variance


SUPPORTED_VARIANCE_METRICS = {
    "revenue": "revenue",
    "transactions": "transactions",
    "units_sold": "units_sold",
    "average_transaction_value": "average_transaction_value",
}


def _build_period_filters(
    filters: dict | None,
    start_date: str,
    end_date: str,
) -> dict:
    """
    Build a governed filter set for one analytical period.

    Existing business filters are preserved while the date range
    is replaced with the requested period.
    """

    normalized_filters = normalize_filters(
        filters
    )

    period_filters = deepcopy(
        normalized_filters
    )

    period_filters["start_date"] = start_date
    period_filters["end_date"] = end_date

    return period_filters


def _resolve_current_period(
    current_start: str | None,
    current_end: str | None,
    filters: dict | None,
) -> tuple[str, str]:
    """
    Resolve the current analytical period.

    If both dates are explicitly supplied, use them.

    If neither date is supplied, use the latest available
    calendar month in the governed analytical scope.

    Partial date ranges are rejected so the agent cannot
    accidentally construct an incomplete analytical period.
    """

    if current_start and current_end:
        return (
            current_start,
            current_end,
        )

    if current_start or current_end:
        raise ValueError(
            "Both current_start and current_end must be "
            "provided when specifying an explicit current period."
        )

    return get_latest_available_month(
        filters=filters,
    )


def get_sales_variance(
    metric_id: str,
    comparison_type: str,
    current_start: str | None = None,
    current_end: str | None = None,
    filters: dict | None = None,
) -> dict:
    """
    Calculate deterministic variance between two analytical periods.

    The same non-date filters are applied to both periods.

    If the current analytical period is not explicitly supplied,
    the latest available sales month is used.

    Args:
        metric_id:
            Governed metric identifier.

        comparison_type:
            Supported comparison type:
            - previous_period
            - previous_month
            - year_over_year

        current_start:
            Optional current analytical period start date in
            YYYY-MM-DD format.

        current_end:
            Optional current analytical period end date in
            YYYY-MM-DD format.

        filters:
            Optional governed analytical filters such as region,
            category, brand, or customer segment.

    Returns:
        Structured variance result containing both periods,
        metric values, absolute change, percentage change,
        and direction.
    """

    normalized_metric_id = (
        metric_id.strip().lower()
        if isinstance(metric_id, str)
        else metric_id
    )

    if normalized_metric_id not in SUPPORTED_VARIANCE_METRICS:
        raise ValueError(
            f"Metric '{metric_id}' does not support variance analysis."
        )

    metric = get_metric(
        normalized_metric_id
    )

    normalized_filters = normalize_filters(
        filters
    )

    resolved_current_start, resolved_current_end = (
        _resolve_current_period(
            current_start=current_start,
            current_end=current_end,
            filters=normalized_filters,
        )
    )

    comparison = resolve_comparison_period(
        current_start=resolved_current_start,
        current_end=resolved_current_end,
        comparison_type=comparison_type,
    )

    current_filters = _build_period_filters(
        filters=normalized_filters,
        start_date=comparison.current_start,
        end_date=comparison.current_end,
    )

    comparison_filters = _build_period_filters(
        filters=normalized_filters,
        start_date=comparison.comparison_start,
        end_date=comparison.comparison_end,
    )

    current_result = get_overall_sales(
        filters=current_filters,
    )

    comparison_result = get_overall_sales(
        filters=comparison_filters,
    )

    metric_key = SUPPORTED_VARIANCE_METRICS[
        normalized_metric_id
    ]

    current_value = float(
        current_result.get(metric_key) or 0
    )

    comparison_value = float(
        comparison_result.get(metric_key) or 0
    )

    variance = calculate_variance(
        current_value=current_value,
        comparison_value=comparison_value,
    )

    return {
        "metric": {
            "id": metric["metric_id"],
            "display_name": metric["display_name"],
        },
        "current_period": {
            "start_date": comparison.current_start,
            "end_date": comparison.current_end,
        },
        "comparison_period": {
            "start_date": comparison.comparison_start,
            "end_date": comparison.comparison_end,
        },
        "comparison_type": comparison.comparison_type,
        "filters": normalized_filters,
        "current_value": variance.current_value,
        "comparison_value": variance.comparison_value,
        "absolute_change": variance.absolute_change,
        "percentage_change": variance.percentage_change,
        "direction": variance.direction,
    }