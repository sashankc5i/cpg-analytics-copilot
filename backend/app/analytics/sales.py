from app.database.repositories.sales_repository import (
    get_monthly_sales_trend_data,
    get_overall_sales_data,
    get_sales_by_region_data,
)


def get_overall_sales(
    filters: dict | None = None,
):
    return get_overall_sales_data(
        filters=filters
    )


def get_sales_by_region(
    filters: dict | None = None,
):
    return get_sales_by_region_data(
        filters=filters
    )


def get_monthly_sales_trend(
    filters: dict | None = None,
):
    return get_monthly_sales_trend_data(
        filters=filters
    )