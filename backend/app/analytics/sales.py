from app.database.repositories.sales_repository import (
    get_monthly_sales_trend_data,
    get_overall_sales_data,
    get_sales_by_region_data,
)


def get_overall_sales():
    return get_overall_sales_data()


def get_sales_by_region():
    return get_sales_by_region_data()


def get_monthly_sales_trend():
    return get_monthly_sales_trend_data()