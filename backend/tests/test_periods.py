from unittest.mock import patch

import pytest

from app.analytics.periods import (
    get_latest_available_month,
    get_latest_available_sales_date,
)


@patch(
    "app.analytics.periods.get_latest_sales_date"
)
def test_get_latest_available_sales_date(
    mock_get_latest_sales_date,
):
    mock_get_latest_sales_date.return_value = (
        "2026-09-30"
    )

    result = get_latest_available_sales_date()

    assert result == "2026-09-30"

    mock_get_latest_sales_date.assert_called_once_with(
        filters=None
    )


@patch(
    "app.analytics.periods.get_latest_sales_date"
)
def test_latest_sales_date_preserves_filters(
    mock_get_latest_sales_date,
):
    filters = {
        "region": ["South"],
        "brand": ["Brand A"],
    }

    mock_get_latest_sales_date.return_value = (
        "2026-09-30"
    )

    result = get_latest_available_sales_date(
        filters=filters
    )

    assert result == "2026-09-30"

    mock_get_latest_sales_date.assert_called_once_with(
        filters=filters
    )


@patch(
    "app.analytics.periods.get_latest_sales_date"
)
def test_latest_sales_date_raises_when_no_data(
    mock_get_latest_sales_date,
):
    mock_get_latest_sales_date.return_value = None

    with pytest.raises(
        ValueError,
        match="No sales data is available",
    ):
        get_latest_available_sales_date()


@patch(
    "app.analytics.periods.get_latest_available_sales_date"
)
def test_latest_available_month(
    mock_get_latest_available_sales_date,
):
    mock_get_latest_available_sales_date.return_value = (
        "2026-09-30"
    )

    result = get_latest_available_month()

    assert result == (
        "2026-09-01",
        "2026-09-30",
    )


@patch(
    "app.analytics.periods.get_latest_available_sales_date"
)
def test_latest_available_month_february(
    mock_get_latest_available_sales_date,
):
    mock_get_latest_available_sales_date.return_value = (
        "2026-02-15"
    )

    result = get_latest_available_month()

    assert result == (
        "2026-02-01",
        "2026-02-28",
    )


@patch(
    "app.analytics.periods.get_latest_available_sales_date"
)
def test_latest_available_month_leap_year(
    mock_get_latest_available_sales_date,
):
    mock_get_latest_available_sales_date.return_value = (
        "2024-02-29"
    )

    result = get_latest_available_month()

    assert result == (
        "2024-02-01",
        "2024-02-29",
    )


@patch(
    "app.analytics.periods.get_latest_available_sales_date"
)
def test_latest_available_month_december(
    mock_get_latest_available_sales_date,
):
    mock_get_latest_available_sales_date.return_value = (
        "2026-12-15"
    )

    result = get_latest_available_month()

    assert result == (
        "2026-12-01",
        "2026-12-31",
    )