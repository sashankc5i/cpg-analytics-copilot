import pytest

from app.analytics.variance_analysis import (
    get_sales_variance,
)
from unittest.mock import patch

def test_revenue_previous_month():
    result = get_sales_variance(
        metric_id="revenue",
        current_start="2026-09-01",
        current_end="2026-09-30",
        comparison_type="previous_month",
    )

    assert result["metric"]["id"] == "revenue"

    assert result["current_period"] == {
        "start_date": "2026-09-01",
        "end_date": "2026-09-30",
    }

    assert result["comparison_period"] == {
        "start_date": "2026-08-01",
        "end_date": "2026-08-31",
    }

    assert isinstance(result["current_value"], float)
    assert isinstance(result["comparison_value"], float)

    assert result["direction"] in {
        "increase",
        "decrease",
        "no_change",
    }


def test_revenue_previous_month_preserves_filters():
    result = get_sales_variance(
        metric_id="revenue",
        current_start="2026-09-01",
        current_end="2026-09-30",
        comparison_type="previous_month",
        filters={
            "region": ["South"],
        },
    )

    assert result["filters"] == {
        "region": ["South"],
    }

    assert result["current_period"]["start_date"] == "2026-09-01"
    assert result["comparison_period"]["start_date"] == "2026-08-01"


def test_transactions_variance():
    result = get_sales_variance(
        metric_id="transactions",
        current_start="2026-09-01",
        current_end="2026-09-30",
        comparison_type="previous_month",
    )

    assert result["metric"]["id"] == "transactions"

    assert isinstance(result["current_value"], float)
    assert isinstance(result["comparison_value"], float)


def test_units_sold_variance():
    result = get_sales_variance(
        metric_id="units_sold",
        current_start="2026-09-01",
        current_end="2026-09-30",
        comparison_type="previous_month",
    )

    assert result["metric"]["id"] == "units_sold"


def test_average_transaction_value_variance():
    result = get_sales_variance(
        metric_id="average_transaction_value",
        current_start="2026-09-01",
        current_end="2026-09-30",
        comparison_type="previous_month",
    )

    assert result["metric"]["id"] == "average_transaction_value"


def test_year_over_year_comparison():
    result = get_sales_variance(
        metric_id="revenue",
        current_start="2026-09-01",
        current_end="2026-09-30",
        comparison_type="year_over_year",
    )

    assert result["current_period"] == {
        "start_date": "2026-09-01",
        "end_date": "2026-09-30",
    }

    assert result["comparison_period"] == {
        "start_date": "2025-09-01",
        "end_date": "2025-09-30",
    }


def test_previous_period_comparison():
    result = get_sales_variance(
        metric_id="revenue",
        current_start="2026-09-01",
        current_end="2026-09-30",
        comparison_type="previous_period",
    )

    assert result["comparison_period"] == {
        "start_date": "2026-08-02",
        "end_date": "2026-08-31",
    }


def test_unsupported_metric_is_rejected():
    with pytest.raises(ValueError):
        get_sales_variance(
            metric_id="stockout_rate",
            current_start="2026-09-01",
            current_end="2026-09-30",
            comparison_type="previous_month",
        )
@patch(
    "app.analytics.variance_analysis.get_latest_available_month"
)
def test_latest_available_month_is_used_when_current_period_is_omitted(
    mock_get_latest_available_month,
):
    mock_get_latest_available_month.return_value = (
        "2026-09-01",
        "2026-09-30",
    )

    result = get_sales_variance(
        metric_id="revenue",
        comparison_type="previous_month",
    )

    assert result["current_period"] == {
        "start_date": "2026-09-01",
        "end_date": "2026-09-30",
    }

    assert result["comparison_period"] == {
        "start_date": "2026-08-01",
        "end_date": "2026-08-31",
    }

    mock_get_latest_available_month.assert_called_once_with(
        filters={}
    )
def test_partial_current_period_is_rejected():
    with pytest.raises(
        ValueError,
        match="Both current_start and current_end",
    ):
        get_sales_variance(
            metric_id="revenue",
            comparison_type="previous_month",
            current_start="2026-09-01",
        )
def test_metric_id_is_case_insensitive():
    result = get_sales_variance(
        metric_id="Revenue",
        current_start="2026-09-01",
        current_end="2026-09-30",
        comparison_type="previous_month",
    )

    assert result["metric"]["id"] == "revenue"