from app.analytics.sales import (
    get_overall_sales,
    get_sales_by_region,
)


def test_regional_revenue_reconciles():
    overall = get_overall_sales()
    regional = get_sales_by_region()

    regional_revenue = sum(
        row["revenue"]
        for row in regional
    )

    assert round(
        regional_revenue,
        2,
    ) == overall["revenue"]


def test_regional_units_reconcile():
    overall = get_overall_sales()
    regional = get_sales_by_region()

    regional_units = sum(
        row["units_sold"]
        for row in regional
    )

    assert regional_units == overall["units_sold"]