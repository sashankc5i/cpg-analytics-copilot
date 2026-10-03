from datetime import date

from app.database.repositories.sales_repository import (
    get_latest_sales_date,
)


def get_latest_available_sales_date(
    filters: dict | None = None,
) -> str:
    """
    Resolve the latest available sales date using governed
    non-date analytical filters.

    Raises:
        ValueError: If no sales data exists for the requested scope.
    """

    latest_date = get_latest_sales_date(
        filters=filters,
    )

    if latest_date is None:
        raise ValueError(
            "No sales data is available for the requested analytical scope."
        )

    return str(latest_date)


def get_latest_available_month(
    filters: dict | None = None,
) -> tuple[str, str]:
    """
    Resolve the calendar month containing the latest available
    sales date.

    Returns:
        Tuple containing:
        - month start date
        - month end date
    """

    latest_sales_date = date.fromisoformat(
        get_latest_available_sales_date(
            filters=filters,
        )
    )

    month_start = latest_sales_date.replace(
        day=1
    )

    if latest_sales_date.month == 12:
        next_month = latest_sales_date.replace(
            year=latest_sales_date.year + 1,
            month=1,
            day=1,
        )
    else:
        next_month = latest_sales_date.replace(
            month=latest_sales_date.month + 1,
            day=1,
        )

    month_end = next_month.fromordinal(
        next_month.toordinal() - 1
    )

    return (
        month_start.isoformat(),
        month_end.isoformat(),
    )